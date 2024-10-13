import ipaddress
import json
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite


class Database:
    db_path = "servers.db"

    @classmethod
    async def init_db(cls):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    domain_name TEXT PRIMARY KEY,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    blocked_by TEXT NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration INTEGER,
                    active BOOLEAN DEFAULT TRUE,
                    manually_unblocked BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (domain_name) REFERENCES domains(domain_name) ON DELETE CASCADE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_info (
                    domain_name TEXT PRIMARY KEY,
                    server_name TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    additional_links TEXT,
                    FOREIGN KEY (domain_name) REFERENCES domains(domain_name) ON DELETE CASCADE
                );
            """)

            await db.commit()

    @classmethod
    async def domain_name_exists(cls, domain_name: str) -> bool:
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT 1 FROM domains WHERE domain_name = ?;
            """,
                (domain_name,),
            ) as cursor:
                return await cursor.fetchone() is not None

    @classmethod
    async def ip_and_port_exists(cls, ip_address: str, port: int) -> bool:
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT 1 FROM domains WHERE ip_address = ? AND port = ?;
            """,
                (ip_address, port),
            ) as cursor:
                return await cursor.fetchone() is not None

    @classmethod
    async def add_domain(
        cls,
        domain_name: str,
        ip_address: str,
        port: int,
        created_by: str,
        description: Optional[str] = None,
    ):
        try:
            ip = ipaddress.ip_address(ip_address)
            if isinstance(ip, ipaddress.IPv6Address):
                raise ValueError("IPv6 addresses are not allowed.")

        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")

        if not (0 <= port <= 65535):
            raise ValueError(
                f"Invalid port number: {port}. It must be between 0 and 65535."
            )

        if await cls.domain_name_exists(domain_name):
            raise ValueError(f"Domain name {domain_name} already exists.")

        if await cls.ip_and_port_exists(ip_address, port):
            raise ValueError(
                f"IP address {ip_address} with port {port} already exists."
            )

        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                """
                INSERT INTO domains (domain_name, ip_address, port, created_by, description)
                VALUES (?, ?, ?, ?, ?);
            """,
                (domain_name, ip_address, port, created_by, description),
            )
            await db.commit()

    @classmethod
    async def delete_domain(cls, domain_name: str):
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM domains WHERE domain_name = ?;", (domain_name,)
            ) as cursor:
                domain = await cursor.fetchone()

                if domain is None:
                    raise ValueError(f"Domain {domain_name} not found.")

            await db.execute(
                "DELETE FROM domains WHERE domain_name = ?;", (domain_name,)
            )
            await db.commit()

    @classmethod
    async def is_block_exists(cls, domain_name: str) -> bool:
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT 1 FROM blocks WHERE domain_name = ? AND active = TRUE;
            """,
                (domain_name,),
            ) as cursor:
                return await cursor.fetchone() is not None

    @classmethod
    async def add_block(
        cls,
        domain_name: str,
        reason: str,
        blocked_by: str,
        duration: Optional[int] = None,
    ):
        if await cls.is_block_exists(domain_name):
            raise ValueError(f"Domain {domain_name} is already blocked.")

        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                """
                INSERT INTO blocks (domain_name, reason, blocked_by, duration)
                VALUES (?, ?, ?, ?);
            """,
                (domain_name, reason, blocked_by, duration),
            )
            await db.commit()

    @classmethod
    async def remove_block(cls, domain_name: str, removed_by: str):
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT active FROM blocks WHERE domain_name = ? AND active = TRUE;
                """,
                (domain_name,),
            ) as cursor:
                block = await cursor.fetchone()

                if block is None:
                    raise ValueError(f"No active block found for domain {domain_name}")

            await db.execute(
                """
                UPDATE blocks 
                SET active = FALSE, manually_unblocked = TRUE
                WHERE domain_name = ? AND active = TRUE;
                """,
                (domain_name,),
            )
            await db.commit()

    @classmethod
    async def add_server_info(
        cls,
        domain_name: str,
        server_name: str,
        description: Optional[str] = None,
        tags: Optional[list] = None,
        additional_links: Optional[dict] = None,
    ):
        tags_str = ",".join(tags) if tags else None
        additional_links_str = (
            json.dumps(additional_links) if additional_links else None
        )

        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                """
                INSERT INTO server_info (domain_name, server_name, description, tags, additional_links)
                VALUES (?, ?, ?, ?, ?);
            """,
                (domain_name, server_name, description, tags_str, additional_links_str),
            )
            await db.commit()

    @classmethod
    async def get_server_info(cls, domain_name: str):
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT server_name, description, tags, additional_links FROM server_info
                WHERE domain_name = ?;
            """,
                (domain_name,),
            ) as cursor:
                server_info = await cursor.fetchone()

                if server_info:
                    server_name, description, tags_str, additional_links_str = (
                        server_info
                    )
                    tags = tags_str.split(",") if tags_str else []
                    additional_links = (
                        json.loads(additional_links_str) if additional_links_str else {}
                    )
                    return server_name, description, tags, additional_links

                return None

    @classmethod
    async def is_domain_blocked(cls, domain_name: str) -> bool:
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                """
                SELECT active, blocked_at, duration, manually_unblocked 
                FROM blocks
                WHERE domain_name = ? AND active = TRUE;
                """,
                (domain_name,),
            ) as cursor:
                block = await cursor.fetchone()

                if block is None:
                    return False

                active, blocked_at, duration, manually_unblocked = block

                if manually_unblocked:
                    return False

                if duration is not None:
                    blocked_at = datetime.fromisoformat(blocked_at)
                    block_end_time = blocked_at + timedelta(seconds=duration)

                    if datetime.now() > block_end_time:
                        await db.execute(
                            "UPDATE blocks SET active = FALSE WHERE domain_name = ?;",
                            (domain_name,),
                        )
                        await db.commit()
                        return False

                return active

    @classmethod
    async def get_domain_info(cls, domain_name: str):
        if await cls.is_domain_blocked(domain_name):
            return None

        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                "SELECT ip_address, port FROM domains WHERE domain_name = ?;",
                (domain_name,),
            ) as cursor:
                return await cursor.fetchone()
