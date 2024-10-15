import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
import bcrypt

from misc import INIT_OWNER_PASSWORD, AccessRights

from .logs_db import LogsDatabase


class RoleAlreadyExistsError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class InsufficientAccessRightsError(Exception):
    pass


class Database:
    _db_path = "dbs/main.db"

    @classmethod
    async def init_db(cls):
        await cls._init_tables()
        await cls._create_base_roles()
        await cls._create_owner()

    @classmethod
    async def _init_tables(cls):
        async with aiosqlite.connect(cls._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS servers_connect (
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    dns_name TEXT NOT NULL,
                    status TEXT DEFAULT 'offline',
                    server_name TEXT NOT NULL UNIQUE,
                    PRIMARY KEY (server_name)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS servers_info (
                    server_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    tags TEXT,
                    additional_links TEXT,
                    owner_email TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (server_name),
                    FOREIGN KEY (server_name) REFERENCES servers_connect(server_name) ON DELETE CASCADE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    server_names TEXT,
                    global_access INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (username)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL CHECK(entity_type IN ('ip', 'server', 'user')),
                    reason TEXT NOT NULL,
                    blocked_by TEXT NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    unblock_at TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    role_name TEXT NOT NULL UNIQUE,
                    permissions INTEGER DEFAULT 0,
                    PRIMARY KEY (role_name)
                );
            """)

            await db.commit()

    @classmethod
    async def _create_owner(cls):
        await cls.create_user(
            "owner",
            INIT_OWNER_PASSWORD,
            "owner",
            AccessRights(AccessRights.FULL_ACCESS),
        )

    @classmethod
    async def _create_base_roles(cls):
        await cls._create_role("owner", AccessRights(AccessRights.FULL_ACCESS))

        await cls._create_role(
            "admin",
            AccessRights(
                AccessRights.BAN_UNBAN
                | AccessRights.VIEW_LOGS
                | AccessRights.MODIFY_ACCESS
            ),
        )

        await cls._create_role(
            "moderator", AccessRights(AccessRights.BAN_UNBAN | AccessRights.VIEW_LOGS)
        )

        await cls._create_role("user", AccessRights())

    @classmethod
    async def get_user_permissions(cls, username: str) -> Optional[AccessRights]:
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT global_access FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return AccessRights(row[0])

                return None

    @classmethod
    async def get_role_permissions(cls, role_name: str) -> Optional[AccessRights]:
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT permissions FROM roles WHERE role_name = ?",
                (role_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return AccessRights(row[0])

                return None

    @classmethod
    async def create_user(
        cls,
        username: str,
        password: str,
        role: str = "user",
        access_rights: AccessRights = AccessRights(),
    ):
        """
        Создаёт нового пользователя. Обрабатывает уникальность username через SQL исключение.
        """
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        try:
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT INTO users (username, hashed_password, global_access, role, created_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        username,
                        hashed_password,
                        int(access_rights),
                        role,
                        datetime.now(timezone.utc),
                    ),
                )
                await db.commit()
                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"User '{username}' created with access rights {str(access_rights)}",
                    importance_level="info",
                )

        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: users.username" in str(e):
                raise UserAlreadyExistsError(f"User '{username}' already exists.")

            else:
                raise

    @classmethod
    async def update_user_access_rights(
        cls,
        username: str,
        new_role: Optional[str] = None,
        new_access_rights: Optional[AccessRights] = None,
    ):
        """
        Обновление прав пользователя:
        - Если указана роль, подтягиваем права из роли.
        - Если роль не найдена, используем указанные права и присваиваем роль 'custom'.
        """
        if new_role:
            role_permissions = await cls.get_role_permissions(new_role)
            if role_permissions is not None:
                new_access_rights = role_permissions

            else:
                new_role = "custom"

        if new_access_rights is None:
            raise ValueError("No valid access rights provided.")

        user_access = await cls.get_user_permissions(username)
        if user_access is None or not user_access.has_access(int(new_access_rights)):
            raise InsufficientAccessRightsError(
                f"User '{username}' does not have sufficient access rights to set '{str(new_access_rights)}'"
            )

        async with aiosqlite.connect(cls._db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET global_access = ?, role = ?
                WHERE username = ?;
                """,
                (int(new_access_rights), new_role or "custom", username),
            )
            await db.commit()

            LogsDatabase.log_system_action(
                server_name=None,
                description=f"User '{username}' updated with access rights {str(new_access_rights)} and role '{new_role}'",
                importance_level="info",
            )

    @classmethod
    async def register(cls, username: str, password: str) -> str:
        await cls.create_user(username, password)
        return await cls.login(username, password)

    @classmethod
    async def login(cls, username: str, password: str) -> str:
        async with aiosqlite.connect(cls._db_path) as db:
            async with db.execute(
                "SELECT username, hashed_password FROM users WHERE username = ?",
                (username,),
            ) as cursor:
                user = await cursor.fetchone()
                if user and bcrypt.checkpw(
                    password.encode("utf-8"), user[1].encode("utf-8")
                ):
                    token = secrets.token_hex(32)
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                    await db.execute(
                        """
                        INSERT INTO tokens (username, token, created_at, expires_at)
                        VALUES (?, ?, ?, ?);
                        """,
                        (user[0], token, datetime.now(timezone.utc), expires_at),
                    )
                    await db.commit()
                    LogsDatabase.log_action(
                        username=user[0],
                        server_name=None,
                        description=f"User '{username}' logged in",
                        importance_level="info",
                    )
                    return token

                raise ValueError("Invalid username or password")

    @classmethod
    async def _create_role(cls, role_name: str, permissions: AccessRights):
        try:
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT INTO roles (role_name, permissions)
                    VALUES (?, ?);
                    """,
                    (role_name, int(permissions)),
                )
                await db.commit()
                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"System created role '{role_name}' with permissions: {str(permissions)}",
                    importance_level="info",
                )
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: roles.role_name" in str(e):
                pass

            else:
                raise

    @classmethod
    async def create_role(
        cls, username: str, role_name: str, permissions: AccessRights
    ):
        try:
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT INTO roles (role_name, permissions)
                    VALUES (?, ?);
                    """,
                    (role_name, int(permissions)),
                )
                await db.commit()
                LogsDatabase.log_action(
                    username=username,
                    server_name=None,
                    description=f"User '{username}' created role '{role_name}' with permissions: {str(permissions)}",
                    importance_level="info",
                )
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: roles.role_name" in str(e):
                raise RoleAlreadyExistsError(f"Role '{role_name}' already exists.")

            else:
                raise

    @classmethod
    async def update_role(
        cls,
        username: str,
        role_name: str,
        new_role_name: Optional[str] = None,
        new_permissions: Optional[AccessRights] = None,
    ):
        try:
            async with aiosqlite.connect(cls._db_path) as db:
                changes = []
                if new_role_name:
                    await db.execute(
                        """
                        UPDATE roles
                        SET role_name = ?
                        WHERE role_name = ?;
                        """,
                        (new_role_name, role_name),
                    )
                    changes.append(f"renamed to '{new_role_name}'")

                if new_permissions:
                    await db.execute(
                        """
                        UPDATE roles
                        SET permissions = ?
                        WHERE role_name = ?;
                        """,
                        (int(new_permissions), new_role_name or role_name),
                    )
                    changes.append(f"permissions updated to '{str(new_permissions)}'")

                await db.commit()

                if changes:
                    LogsDatabase.log_action(
                        username=username,
                        server_name=None,
                        description=f"User '{username}' updated role '{role_name}': {', '.join(changes)}",
                        importance_level="info",
                    )

        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: roles.role_name" in str(e):
                raise RoleAlreadyExistsError(f"Role '{new_role_name}' already exists.")

            else:
                raise

    @classmethod
    async def delete_role(cls, username: str, role_name: str):
        async with aiosqlite.connect(cls._db_path) as db:
            await db.execute(
                """
                DELETE FROM roles
                WHERE role_name = ?;
                """,
                (role_name,),
            )
            await db.commit()
            LogsDatabase.log_action(
                username=username,
                server_name=None,
                description=f"User '{username}' deleted role '{role_name}'",
                importance_level="info",
            )
