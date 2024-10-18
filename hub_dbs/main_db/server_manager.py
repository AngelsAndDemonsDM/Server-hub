import ipaddress
import secrets
from typing import Literal, Optional

import aiosqlite
import bcrypt

from hub_dbs.logs_db import LogsDatabase

from .bans_manager import BanManager
from .database import Database
from .errors import BanError


class ServerManager:
    StatusType = Literal["offline", "online", "maintenance"]

    @classmethod
    def _hash_token(cls, token: str) -> str:
        return bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def verify_token(cls, token: str, token_hash: str) -> bool:
        return bcrypt.checkpw(token.encode("utf-8"), token_hash.encode("utf-8"))

    @classmethod
    async def get_all_active_servers(cls) -> list[dict]:
        active_servers = []
        
        async with Database() as db:
            async with db.execute(
                """
                SELECT server_name, dns_name, ip_address, port, current_players, max_players
                FROM servers_connect
                WHERE status = 'online';
                """
            ) as cursor:
                servers = await cursor.fetchall()
                for server in servers:
                    active_servers.append({
                        "server_name": server[0],
                        "dns_name": server[1],
                        "ip_address": server[2],
                        "port": server[3],
                        "current_players": server[4],
                        "max_players": server[5],
                    })

        return active_servers

    @classmethod
    async def get_server_info(cls, dns_name: str) -> Optional[dict]:
        async with Database() as db:
            async with db.execute(
                """
                SELECT server_name, ip_address, port, status, max_players, current_players
                FROM servers_connect
                WHERE dns_name = ?;
                """,
                (dns_name,),
            ) as cursor:
                server_row = await cursor.fetchone()
                
            if not server_row:
                return None
            
            server_info = {
                "server_name": server_row[0],
                "ip_address": server_row[1],
                "port": server_row[2],
                "status": server_row[3],
                "max_players": server_row[4],
                "current_players": server_row[5],
            }

        return server_info

    @classmethod
    async def add_server(
        cls,
        username: str,
        server_name: str,
        dns_name: str,
        ip_address: str,
        port: int,
        max_players: int,
        current_players: int = 0,
        status: StatusType = "offline",
        description: Optional[str] = None,
        tags: Optional[str] = None,
        additional_links: Optional[str] = None,
    ):
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")

        if await BanManager.is_banned(ip_address, "ip"):
            raise BanError("IP address is banned")

        if current_players > max_players:
            raise ValueError("Current players cannot exceed max players.")

        async with Database() as db:
            try:
                await db.execute(
                    """
                    INSERT INTO servers_connect (server_name, dns_name, ip_address, port, status, max_players, current_players)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        server_name,
                        dns_name,
                        ip_address,
                        port,
                        status,
                        max_players,
                        current_players,
                    ),
                )
                await db.execute(
                    """
                    INSERT INTO servers_info (dns_name, description, tags, additional_links, username)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (dns_name, description, tags, additional_links, username),
                )

                LogsDatabase.log_action(
                    username=username,
                    server_name=server_name,
                    description=f"Server '{server_name}' added with status '{status}'",
                    importance_level="info",
                )
            except aiosqlite.IntegrityError as e:
                if (
                    "UNIQUE constraint failed: servers_connect.ip_address, servers_connect.port"
                    in str(e)
                ):
                    raise ValueError(
                        f"Server with IP {ip_address} and port {port} already exists."
                    )

                raise

    @classmethod
    async def delete_server(cls, username: str, dns_name: str):
        async with Database() as db:
            await db.execute(
                """
                DELETE FROM servers_connect WHERE dns_name = ?;
                """,
                (dns_name,),
            )
            await db.execute(
                """
                DELETE FROM servers_info WHERE dns_name = ?;
                """,
                (dns_name,),
            )
            LogsDatabase.log_action(
                username=username,
                server_name=dns_name,
                description=f"Server '{dns_name}' was deleted.",
                importance_level="info",
            )

    @classmethod
    async def update_server_info(
        cls,
        dns_name: str,
        server_name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        additional_links: Optional[str] = None,
        max_players: Optional[int] = None,
    ):
        async with Database() as db:
            if server_name:
                await db.execute(
                    """
                    UPDATE servers_connect
                    SET server_name = ?
                    WHERE dns_name = ?;
                    """,
                    (server_name, dns_name),
                )

            if max_players:
                await db.execute(
                    """
                    UPDATE servers_connect
                    SET max_players = ?
                    WHERE dns_name = ?;
                    """,
                    (max_players, dns_name),
                )

            await db.execute(
                """
                UPDATE servers_info
                SET description = ?, tags = ?, additional_links = ?
                WHERE dns_name = ?;
                """,
                (description, tags, additional_links, dns_name),
            )

    @classmethod
    async def update_server_players(cls, dns_name: str, current_players: int):
        async with Database() as db:
            await db.execute(
                """
                UPDATE servers_connect
                SET current_players = ?
                WHERE dns_name = ?;
                """,
                (
                    current_players,
                    dns_name,
                ),
            )

    @classmethod
    async def update_server_status(cls, dns_name: str, status: StatusType):
        async with Database() as db:
            await db.execute(
                """
                UPDATE servers_connect
                SET status = ?
                WHERE dns_name = ?;
                """,
                (
                    status,
                    dns_name,
                ),
            )

    @classmethod
    async def generate_api_token(cls, username: str, dns_name: str) -> str:
        async with Database() as db:
            async with db.execute(
                """
                SELECT username FROM servers_info WHERE dns_name = ?;
                """,
                (dns_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != username:
                    raise PermissionError(
                        f"User '{username}' is not the owner of the server '{dns_name}'."
                    )

        token = secrets.token_hex(32)
        token_hash = cls._hash_token(token)

        async with Database() as db:
            await db.execute(
                """
                INSERT INTO api_tokens (token, dns_name)
                VALUES (?, ?);
                """,
                (token_hash, dns_name),
            )

            LogsDatabase.log_action(
                username=username,
                server_name=dns_name,
                description=f"API token generated for server '{dns_name}' by '{username}'",
                importance_level="info",
            )

        return token

    @classmethod
    async def revoke_api_token(cls, username: str, token: str):
        async with Database() as db:
            async with db.execute(
                """
                SELECT token, dns_name FROM api_tokens WHERE dns_name = ?;
                """,
                (token,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Token '{token}' not found.")
                token_hash, dns_name = row

            async with db.execute(
                """
                SELECT username FROM servers_info WHERE dns_name = ?;
                """,
                (dns_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] != username:
                    raise PermissionError(
                        f"User '{username}' is not the owner of the server '{dns_name}'."
                    )

            if not cls.verify_token(token, token_hash):
                raise ValueError("Invalid token provided.")

            await db.execute(
                """
                DELETE FROM api_tokens WHERE token = ?;
                """,
                (token_hash,),
            )

            LogsDatabase.log_action(
                username=username,
                server_name=dns_name,
                description=f"API token for '{dns_name}' revoked by '{username}'",
                importance_level="info",
            )

    @classmethod
    async def get_api_token(cls, dns_name: str) -> Optional[str]:
        async with Database() as db:
            async with db.execute(
                "SELECT token FROM api_tokens WHERE dns_name = ?;",
                (dns_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]

        return None
