from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from hub_dbs.logs_db import LogsDatabase

from .database import Database


class BanManager:
    EntityType = Literal["user", "ip"]
    
    @classmethod
    async def system_add_ban(
        cls,
        entity_name: str,
        entity_type: EntityType,
        reason: str,
        duration: Optional[timedelta] = None,
    ):
        """Системный бан, используется администраторами для добавления бана."""
        await cls._add_ban(
            entity_name, entity_type, reason, "system", duration, system=True
        )

    @classmethod
    async def user_add_ban(
        cls,
        username: str,
        entity_name: str,
        entity_type: EntityType,
        reason: str,
        duration: Optional[timedelta] = None,
    ):
        """Пользовательский бан, где пользователь может банить, например, спамеров."""
        await cls._add_ban(
            entity_name,
            entity_type,
            reason,
            username,
            duration,
            system=False,
        )

    @classmethod
    async def _add_ban(
        cls,
        entity_name: str,
        entity_type: EntityType,
        reason: str,
        blocked_by: str,
        duration: Optional[timedelta],
        system: bool,
    ):
        """Внутренний метод добавления бана с разделением по типу: системный или пользовательский."""
        unblock_at = datetime.now(timezone.utc) + duration if duration else None

        async with Database() as db:
            await db.execute(
                """
                INSERT INTO blocks (entity_name, entity_type, reason, blocked_by, blocked_at, unblock_at, active)
                VALUES (?, ?, ?, ?, ?, ?, TRUE);
                """,
                (
                    entity_name,
                    entity_type,
                    reason,
                    blocked_by,
                    datetime.now(timezone.utc),
                    unblock_at,
                ),
            )

            if system:
                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"System ban added for '{entity_name}' ({entity_type})",
                    importance_level="info",
                )

            else:
                LogsDatabase.log_action(
                    username=blocked_by,
                    server_name=None,
                    description=f"User '{blocked_by}' added ban for '{entity_name}' ({entity_type})",
                    importance_level="info",
                )

    @classmethod
    async def system_remove_ban(
        cls, entity_name: str, entity_type: Literal["user", "ip"]
    ):
        """Системный метод для снятия бана."""
        await cls._remove_ban(entity_name, entity_type, system=True)

    @classmethod
    async def user_remove_ban(
        cls, username: str, entity_name: str, entity_type: Literal["user", "ip"]
    ):
        """Пользовательский метод для снятия бана."""
        await cls._remove_ban(entity_name, entity_type, system=False, username=username)

    @classmethod
    async def _remove_ban(
        cls,
        entity_name: str,
        entity_type: EntityType,
        system: bool,
        username: Optional[str] = None,
    ):
        """Внутренний метод снятия бана с разделением по типу: системный или пользовательский."""
        async with Database() as db:
            await db.execute(
                """
                UPDATE blocks
                SET active = FALSE
                WHERE entity_name = ? AND entity_type = ?;
                """,
                (entity_name, entity_type),
            )

            if system:
                LogsDatabase.log_system_action(
                    server_name=None,
                    description=f"System ban removed from '{entity_name}' ({entity_type})",
                    importance_level="info",
                )
            else:
                LogsDatabase.log_action(
                    username=username if username else "error in rm_ban_logic",
                    server_name=None,
                    description=f"User '{username}' removed ban for '{entity_name}' ({entity_type})",
                    importance_level="info",
                )

    @classmethod
    async def is_banned(
        cls, entity_name: str, entity_type: Literal["user", "ip"]
    ) -> bool:
        """Проверяет, есть ли активный бан для указанного пользователя или IP."""
        async with Database() as db:
            async with db.execute(
                """
                SELECT unblock_at FROM blocks
                WHERE entity_name = ? AND entity_type = ? AND active = TRUE;
                """,
                (entity_name, entity_type),
            ) as cursor:
                ban = await cursor.fetchone()
                if ban:
                    unblock_at = ban[0]
                    if unblock_at and datetime.now(
                        timezone.utc
                    ) > datetime.fromisoformat(unblock_at):
                        await cls.system_remove_ban(entity_name, entity_type)
                        return False

                    return True

                return False
