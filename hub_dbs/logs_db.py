import asyncio
from datetime import datetime, timezone
from typing import Optional, Literal

import aiosqlite


class LogsDatabase:
    _db_path = "dbs/logs.db"

    IMPORTANCE_LEVEL = Literal["info", "warning", "error", "critical"]

    @classmethod
    async def init_db(cls):
        async with aiosqlite.connect(cls._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    server_name TEXT,
                    description TEXT,
                    importance_level TEXT DEFAULT 'info',
                    source TEXT NOT NULL DEFAULT 'user',
                    timestamp TIMESTAMP NOT NULL
                );
            """)
            await db.commit()

    @staticmethod
    def log_action(
        username: str,
        server_name: Optional[str],
        description: str,
        importance_level: IMPORTANCE_LEVEL = "info",
    ):
        asyncio.create_task(
            LogsDatabase._log_action_async(
                username,
                server_name,
                importance_level,
                datetime.now(timezone.utc),
                "user",
                description,
            )
        )

    @staticmethod
    def log_system_action(
        server_name: Optional[str],
        description: str,
        importance_level: IMPORTANCE_LEVEL = "info",
    ):
        asyncio.create_task(
            LogsDatabase._log_action_async(
                None,
                server_name,
                importance_level,
                datetime.now(timezone.utc),
                "system",
                description,
            )
        )

    @classmethod
    async def _log_action_async(
        cls,
        username: Optional[str],
        server_name: Optional[str],
        importance_level: IMPORTANCE_LEVEL,
        timestamp: datetime,
        source: str,
        description: str,
    ):
        async with aiosqlite.connect(cls._db_path) as db:
            await db.execute(
                """
                INSERT INTO logs (username, server_name, importance_level, source, timestamp, description)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    username,
                    server_name,
                    importance_level,
                    source,
                    timestamp,
                    description,
                ),
            )
            await db.commit()

    @classmethod
    async def get_logs_by_user(cls, username: str):
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT * FROM logs WHERE username = ? ORDER BY timestamp DESC;",
                (username,),
            ) as cursor:
                return await cursor.fetchall()

    @classmethod
    async def get_logs_by_server(cls, server_name: str):
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT * FROM logs WHERE server_name = ? ORDER BY timestamp DESC;",
                (server_name,),
            ) as cursor:
                return await cursor.fetchall()

    @classmethod
    async def get_logs_by_importance(cls, importance_level: IMPORTANCE_LEVEL):
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT * FROM logs WHERE importance_level = ? ORDER BY timestamp DESC;",
                (importance_level,),
            ) as cursor:
                return await cursor.fetchall()

    @classmethod
    async def get_logs_by_date_range(cls, start_date: datetime, end_date: datetime):
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT * FROM logs WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC;",
                (start_date, end_date),
            ) as cursor:
                return await cursor.fetchall()

    @classmethod
    async def get_logs_by_source(cls, source: str):
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT * FROM logs WHERE source = ? ORDER BY timestamp DESC;",
                (source,),
            ) as cursor:
                return await cursor.fetchall()
