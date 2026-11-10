from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import create_engine_and_sessionmaker  # noqa: E402
from app.models import User  # noqa: E402


def _valid_password(password: str) -> bool:
    return len(password) >= 10 and any(ch.isalpha() for ch in password) and any(
        ch.isdigit() for ch in password
    )


async def _upsert_admin(username: str, password: str, display_name: str, unit: str | None) -> None:
    engine, sessionmaker = create_engine_and_sessionmaker(get_settings().database_url)
    async with sessionmaker() as session:
        user = (
            await session.execute(select(User).where(User.username == username))
        ).scalars().first()
        if user is None:
            user = User(username=username, display_name=display_name)
            session.add(user)
        user.display_name = display_name
        user.unit = unit
        user.role = "admin"
        user.status = "active"
        user.must_change_password = False
        user.password_hash = hash_password(password)
        await session.commit()
    await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or reset a local Demo v0 admin account.")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--display-name", default="演示管理员")
    parser.add_argument("--unit", default="演示单位")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password: ")
    if not _valid_password(password):
        print("password must be at least 10 chars and contain letters and digits", file=sys.stderr)
        return 2

    asyncio.run(_upsert_admin(args.username, password, args.display_name, args.unit))
    print(f"admin ready: {args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
