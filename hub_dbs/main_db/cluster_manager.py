from typing import Optional

from hub_dbs.logs_db import LogsDatabase

from .database import Database


class ClusterManager:
    @classmethod
    async def create_cluster(
        cls, cluster_dns_name: str, username: str, description: Optional[str] = None
    ):
        """Создает новый кластер серверов."""
        async with Database() as db:
            await db.execute(
                """
                INSERT INTO server_clusters (cluster_dns_name, description)
                VALUES (?, ?);
                """,
                (cluster_dns_name, description),
            )

        LogsDatabase.log_action(
            username=username,
            server_name=None,
            description=f"Cluster '{cluster_dns_name}' created by '{username}'",
            importance_level="info",
        )

    @classmethod
    async def add_server_to_cluster(
        cls, cluster_dns_name: str, dns_name: str, username: str
    ):
        """Добавляет сервер в кластер."""
        async with Database() as db:
            await db.execute(
                """
                INSERT INTO cluster_servers_unit (cluster_dns_name, dns_name)
                VALUES (?, ?);
                """,
                (cluster_dns_name, dns_name),
            )

        LogsDatabase.log_action(
            username=username,
            server_name=dns_name,
            description=f"Server '{dns_name}' added to cluster '{cluster_dns_name}' by '{username}'",
            importance_level="info",
        )

    @classmethod
    async def remove_server_from_cluster(
        cls, cluster_dns_name: str, dns_name: str, username: str
    ):
        """Удаляет сервер из кластера."""
        async with Database() as db:
            await db.execute(
                """
                DELETE FROM cluster_servers_unit
                WHERE cluster_dns_name = ? AND dns_name = ?;
                """,
                (cluster_dns_name, dns_name),
            )

        LogsDatabase.log_action(
            username=username,
            server_name=dns_name,
            description=f"Server '{dns_name}' removed from cluster '{cluster_dns_name}' by '{username}'",
            importance_level="info",
        )

    @classmethod
    async def delete_cluster(cls, cluster_dns_name: str, username: str):
        """Удаляет кластер и все его связи с серверами."""
        async with Database() as db:
            await db.execute(
                """
                DELETE FROM server_clusters WHERE cluster_dns_name = ?;
                """,
                (cluster_dns_name,),
            )
            await db.execute(
                """
                DELETE FROM cluster_servers_unit WHERE cluster_dns_name = ?;
                """,
                (cluster_dns_name,),
            )

        LogsDatabase.log_action(
            username=username,
            server_name=None,
            description=f"Cluster '{cluster_dns_name}' deleted by '{username}'",
            importance_level="info",
        )

    @classmethod
    async def get_cluster_info(cls, cluster_dns_name: str) -> Optional[dict]:
        """Возвращает информацию о кластере и список серверов, входящих в него."""
        async with Database() as db:
            async with db.execute(
                """
                SELECT cluster_dns_name, description
                FROM server_clusters
                WHERE cluster_dns_name = ?;
                """,
                (cluster_dns_name,),
            ) as cursor:
                cluster_info = await cursor.fetchone()

            if not cluster_info:
                return None

            async with db.execute(
                """
                SELECT dns_name
                FROM cluster_servers_unit
                WHERE cluster_dns_name = ?;
                """,
                (cluster_dns_name,),
            ) as cursor:
                servers = await cursor.fetchall()

            server_list = [server[0] for server in servers]

            return {
                "cluster_dns_name": cluster_info[0],
                "description": cluster_info[1],
                "servers": server_list,
            }

    @classmethod
    async def get_least_loaded_server(cls, cluster_dns_name: str) -> Optional[dict]:
        """Возвращает сервер с наименьшим количеством активных игроков в кластере, при этом сервер должен быть онлайн."""
        async with Database() as db:
            async with db.execute(
                """
                SELECT sc.server_name, sc.dns_name, sc.ip_address, sc.port, sc.current_players, sc.max_players
                FROM servers_connect sc
                JOIN cluster_servers_unit csu ON sc.dns_name = csu.dns_name
                WHERE csu.cluster_dns_name = ? AND sc.status = 'online'
                ORDER BY sc.current_players ASC
                LIMIT 1;
                """,
                (cluster_dns_name,),
            ) as cursor:
                server_info = await cursor.fetchone()
                if server_info:
                    return {
                        "server_name": server_info[0],
                        "dns_name": server_info[1],
                        "ip_address": server_info[2],
                        "port": server_info[3],
                        "current_players": server_info[4],
                        "max_players": server_info[5],
                    }
                return None
