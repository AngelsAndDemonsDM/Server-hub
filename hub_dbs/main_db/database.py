import aiosqlite


class Database:
    _db_path = "dbs/main.db"

    @classmethod
    async def init_tables(cls):
        async with aiosqlite.connect(cls._db_path) as db:
            # Кластеры серверов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_clusters (
                    cluster_dns_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    PRIMARY KEY (cluster_dns_name)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS cluster_servers_unit (
                    cluster_dns_name TEXT NOT NULL,
                    dns_name TEXT NOT NULL,
                    PRIMARY KEY (dns_name)
                    FOREIGN KEY (cluster_dns_name) REFERENCES server_clusters(cluster_dns_name) ON DELETE CASCADE,
                    FOREIGN KEY (dns_name) REFERENCES servers_connect(dns_name) ON DELETE CASCADE
                );
            """)

            # Блок серверов. Подключение и прочая информация
            await db.execute("""
                CREATE TABLE IF NOT EXISTS servers_connect (
                    server_name TEXT NOT NULL UNIQUE,
                    dns_name TEXT NOT NULL UNIQUE,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    max_players INTEGER NOT NULL, 
                    current_players INTEGER NOT NULL,
                    status TEXT DEFAULT 'offline' CHECK(status IN ('offline', 'online', 'maintenance')),
                    PRIMARY KEY (dns_name)
                    UNIQUE (ip_address, port)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS servers_info (
                    dns_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    tags TEXT,
                    additional_links TEXT,
                    username TEXT NOT NULL,
                    PRIMARY KEY (dns_name),
                    FOREIGN KEY (dns_name) REFERENCES servers_connect(dns_name) ON DELETE CASCADE,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE SET NULL
                );
            """)

            # Таблица для API токенов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    dns_name TEXT NOT NULL,
                    FOREIGN KEY (dns_name) REFERENCES servers_connect(dns_name) ON DELETE CASCADE
                );
            """)

            # Блок пользователей. Роли и права, токены
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    dns_name TEXT,
                    global_access INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'user',
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

            # Служебное. Баны, роли
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL CHECK(entity_type IN ('ip', 'user')),
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

    async def __aenter__(self):
        """Открывает подключение к базе данных и начинает транзакцию."""
        self.connection = await aiosqlite.connect(self._db_path)
        await self.connection.execute("BEGIN")
        return self.connection

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Завершает транзакцию: фиксирует изменения (commit) или откатывает (rollback), если произошла ошибка."""
        if exc_type is None:
            await self.connection.commit()

        else:
            await self.connection.rollback()

        await self.connection.close()
