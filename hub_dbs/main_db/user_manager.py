import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
import bcrypt

from hub_dbs.logs_db import LogsDatabase
from misc import INIT_OWNER_PASSWORD, AccessRights

from .bans_manager import BanManager
from .database import Database
from .errors import (BanError, InsufficientAccessRightsError,
                     UserAlreadyExistsError)


class UserManager:
    @classmethod
    def _hash_token(cls, token: str) -> str:
        return bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def _verify_token(cls, token: str, token_hash: str) -> bool:
        return bcrypt.checkpw(token.encode("utf-8"), token_hash.encode("utf-8"))

    @classmethod
    async def init_manager(cls):
        await cls.system_create_user(
            "owner",
            INIT_OWNER_PASSWORD,
            "owner",
            AccessRights(AccessRights.FULL_ACCESS),
        )

    @classmethod
    async def get_user_by_token(cls, token: str) -> Optional[str]:
        async with Database() as db:
            async with db.execute(
                "SELECT username, token, expires_at FROM tokens;"
            ) as cursor:
                tokens = await cursor.fetchall()

                for user, token_hash, expires_at in tokens:
                    if cls._verify_token(token, token_hash):
                        if datetime.now(timezone.utc) < datetime.fromisoformat(
                            expires_at
                        ):
                            return user
                        else:
                            await db.execute(
                                "DELETE FROM tokens WHERE token = ?;", (token_hash,)
                            )
                            return None

        return None

    @classmethod
    async def get_user_permissions(cls, username: str) -> Optional[AccessRights]:
        async with Database() as db:
            async with db.execute(
                "SELECT global_access FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return AccessRights(row[0])

                return None

    @classmethod
    async def get_role_permissions(cls, role_name: str) -> Optional[AccessRights]:
        async with Database() as db:
            async with db.execute(
                "SELECT permissions FROM roles WHERE role_name = ?",
                (role_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return AccessRights(row[0])

                return None

    @classmethod
    async def system_create_user(
        cls,
        username: str,
        password: str,
        role: str = "user",
        access_rights: AccessRights = AccessRights(),
    ):
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        try:
            async with Database() as db:
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

                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"System create user '{username}' with access rights {str(access_rights)}",
                    importance_level="info",
                )

        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed: users.username" in str(e):
                pass

            else:
                raise

    @classmethod
    async def create_user(
        cls,
        username: str,
        password: str,
        role: str = "user",
        access_rights: AccessRights = AccessRights(),
    ):
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        try:
            async with Database() as db:
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

        async with Database() as db:
            await db.execute(
                """
                UPDATE users
                SET global_access = ?, role = ?
                WHERE username = ?;
                """,
                (int(new_access_rights), new_role or "custom", username),
            )

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
        if await BanManager.is_banned(username, "user"):
            raise BanError("This user is banned.")

        async with Database() as db:
            async with db.execute(
                "SELECT username, hashed_password FROM users WHERE username = ?",
                (username,),
            ) as cursor:
                user = await cursor.fetchone()
                if user and bcrypt.checkpw(
                    password.encode("utf-8"), user[1].encode("utf-8")
                ):
                    token = secrets.token_hex(32)
                    token_hash = cls._hash_token(token)
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                    await db.execute(
                        """
                        INSERT INTO tokens (username, token, created_at, expires_at)
                        VALUES (?, ?, ?, ?);
                        """,
                        (user[0], token_hash, datetime.now(timezone.utc), expires_at),
                    )

                    LogsDatabase.log_action(
                        username=user[0],
                        server_name=None,
                        description=f"User '{username}' logged in",
                        importance_level="info",
                    )
                    return token

                raise ValueError("Invalid username or password")

    @classmethod
    async def logout(cls, token: str):
        username = await cls.get_user_by_token(token)
        if username is None:
            raise ValueError("Invalid token")

        async with Database() as db:
            await db.execute(
                "DELETE FROM tokens WHERE username = ?;",
                (username,),
            )

            LogsDatabase.log_action(
                username=username,
                server_name=None,
                description=f"User '{username}' logged out (token '{token}' removed)",
                importance_level="info",
            )

    @classmethod
    async def full_logout(cls, token: str):
        username = await cls.get_user_by_token(token)
        if username is None:
            raise ValueError("Invalid token")

        async with Database() as db:
            await db.execute(
                "DELETE FROM tokens WHERE username = ?;",
                (username,),
            )

            LogsDatabase.log_action(
                username=username,
                server_name=None,
                description=f"User '{username}' logged out completely (all tokens removed)",
                importance_level="info",
            )
