from typing import Optional

import aiosqlite

from hub_dbs.logs_db import LogsDatabase
from misc import AccessRights

from .database import Database
from .errors import RoleAlreadyExistsError


class RoleManager:
    @classmethod
    async def init_manager(cls):
        await cls.system_create_role("owner", AccessRights(AccessRights.FULL_ACCESS))

        await cls.system_create_role(
            "admin",
            AccessRights(
                AccessRights.BAN_UNBAN
                | AccessRights.VIEW_LOGS
                | AccessRights.MODIFY_ACCESS
            ),
        )

        await cls.system_create_role(
            "moderator", AccessRights(AccessRights.BAN_UNBAN | AccessRights.VIEW_LOGS)
        )

        await cls.system_create_role("user", AccessRights())

    @classmethod
    async def system_create_role(cls, role_name: str, permissions: AccessRights):
        try:
            async with Database() as db:
                await db.execute(
                    """
                    INSERT INTO roles (role_name, permissions)
                    VALUES (?, ?);
                    """,
                    (role_name, int(permissions)),
                )

                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"System created role '{role_name}' with permissions: {str(permissions)}",
                    importance_level="info",
                )

        except aiosqlite.IntegrityError as err:
            if "UNIQUE constraint failed: roles.role_name" in str(err):
                pass

            else:
                raise

    @classmethod
    async def create_role(
        cls, username: str, role_name: str, permissions: AccessRights
    ):
        try:
            async with Database() as db:
                await db.execute(
                    """
                    INSERT INTO roles (role_name, permissions)
                    VALUES (?, ?);
                    """,
                    (role_name, int(permissions)),
                )

                LogsDatabase.log_action(
                    username=username,
                    server_name=None,
                    description=f"User '{username}' created role '{role_name}' with permissions: {str(permissions)}",
                    importance_level="info",
                )
        except aiosqlite.IntegrityError as err:
            if "UNIQUE constraint failed: roles.role_name" in str(err):
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
            async with Database() as db:
                changes = []

                if new_role_name:
                    async with db.execute(
                        "SELECT role_name FROM roles WHERE role_name = ?",
                        (new_role_name,),
                    ) as cursor:
                        if await cursor.fetchone():
                            raise RoleAlreadyExistsError(
                                f"Role '{new_role_name}' already exists."
                            )

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

                if changes:
                    LogsDatabase.log_action(
                        username=username,
                        server_name=None,
                        description=f"User '{username}' updated role '{role_name}': {', '.join(changes)}",
                        importance_level="info",
                    )

        except aiosqlite.IntegrityError as err:
            if "UNIQUE constraint failed: roles.role_name" in str(err):
                raise RoleAlreadyExistsError(f"Role '{new_role_name}' already exists.")

            else:
                raise

    @classmethod
    async def delete_role(cls, username: str, role_name: str):
        async with Database() as db:
            await db.execute(
                """
                DELETE FROM roles
                WHERE role_name = ?;
                """,
                (role_name,),
            )

            LogsDatabase.log_action(
                username=username,
                server_name=None,
                description=f"User '{username}' deleted role '{role_name}'",
                importance_level="info",
            )
