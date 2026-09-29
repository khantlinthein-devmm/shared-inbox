"""Bootstrap the first admin account (no default passwords).

Usage:
    python create_admin.py --email you@company.com [--name "Owner"] [--role admin]
    python create_admin.py --email agent@company.com --role agent

The password is read from --password, the ADMIN_PASSWORD env var (CI only),
or prompted securely via getpass. Fails if the email already exists.
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, UserRole
from init_db import migrate


def _resolve_password(cli_value: str | None) -> str:
    if cli_value:
        password = cli_value
    elif os.getenv("ADMIN_PASSWORD"):
        password = os.getenv("ADMIN_PASSWORD", "")
    else:
        password = getpass.getpass("Password (min 6 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(1)
    if len(password) < 6:
        print("Password must be at least 6 characters.", file=sys.stderr)
        sys.exit(1)
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a user account (bootstrap)")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--name", default="System Admin", help="Full name")
    parser.add_argument("--role", default="admin", choices=["admin", "agent"], help="Role")
    parser.add_argument("--password", default=None, help="Password (else prompted securely)")
    args = parser.parse_args()
    password = _resolve_password(args.password)
    migrate()
    asyncio.run(_create_user(args, password))


async def _create_user(args: argparse.Namespace, password: str) -> None:
    email = args.email.strip().lower()
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"User already exists: {email} (id={existing.id}, role={existing.role})", file=sys.stderr)
            sys.exit(1)
        user = User(
            email=email,
            full_name=args.name.strip() or email,
            role=UserRole.admin.value if args.role == "admin" else UserRole.agent.value,
            hashed_password=hash_password(password),
        )
        db.add(user)
        await db.commit()
        print(f"Created {args.role}: {email} (id={user.id})")


if __name__ == "__main__":
    main()
