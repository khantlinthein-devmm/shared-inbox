"""Create database tables.

Usage:
    python init_db.py

No users are seeded. Create the first admin account with:
    python create_admin.py --email you@company.com
"""

import asyncio

from app.core.database import Base, engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")
    print("No users seeded. Run: python create_admin.py --email you@company.com")


if __name__ == "__main__":
    asyncio.run(main())
