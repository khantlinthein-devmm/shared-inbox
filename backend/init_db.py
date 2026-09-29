"""Bring the database schema up to date. Runs on every container start.

Usage:
    python init_db.py

Applies Alembic migrations (backend/migrations). Databases created before
migrations existed are detected and adopted without losing data.

No users are seeded. Create the first admin account with:
    python create_admin.py --email you@company.com

To change the schema: edit the models, then
    alembic revision --autogenerate -m "describe the change"
"""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401  registers every model on Base.metadata
from app.core.database import Base, engine

BASELINE = "0001"
# Tables that create_all added to pre-migration databases after they were first
# created; such a database may still be missing them.
LATE_BASELINE_TABLES = ("quick_replies",)


async def _adopt_legacy_database() -> bool:
    """Return True if this is a pre-migration database that must be stamped at the baseline.

    Those databases have the app's tables but no alembic_version table. Any
    baseline table they are missing is created first so the stamp is truthful.
    """
    try:
        async with engine.begin() as conn:
            tables = set(await conn.run_sync(lambda c: inspect(c).get_table_names()))
            if "alembic_version" in tables or "conversations" not in tables:
                return False
            missing = [Base.metadata.tables[name] for name in LATE_BASELINE_TABLES if name not in tables]
            if missing:
                await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=missing))
            return True
    finally:
        await engine.dispose()


def migrate() -> None:
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    if asyncio.run(_adopt_legacy_database()):
        command.stamp(config, BASELINE)
        print(f"Existing database adopted at migration {BASELINE}.")
    command.upgrade(config, "head")
    print("Database schema is up to date.")


if __name__ == "__main__":
    migrate()
    print("No users seeded. Run: python create_admin.py --email you@company.com")
