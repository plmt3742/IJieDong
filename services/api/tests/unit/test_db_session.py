from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import create_engine_and_sessionmaker


def test_sqlite_foreign_keys_and_wal(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'pragma.db'}"
    engine, _ = create_engine_and_sessionmaker(database_url)

    async def run() -> None:
        async with engine.begin() as connection:
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar_one()
            journal_mode = (await connection.execute(text("PRAGMA journal_mode"))).scalar_one()
            assert foreign_keys == 1
            assert str(journal_mode).lower() == "wal"

            await connection.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
            await connection.execute(
                text(
                    "CREATE TABLE child ("
                    "id INTEGER PRIMARY KEY, "
                    "parent_id INTEGER REFERENCES parent(id)"
                    ")"
                )
            )
            try:
                await connection.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 999)"))
            except IntegrityError:
                pass
            else:
                raise AssertionError("SQLite foreign key enforcement is disabled")
        await engine.dispose()

    asyncio.run(run())
