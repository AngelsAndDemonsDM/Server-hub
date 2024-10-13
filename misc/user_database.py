import aiosqlite
import bcrypt
import uuid
from typing import Optional, Literal


class UserDatabase:
    db_path = "user.db"

    Roles = Literal["system", "admin", "moderator", "user"]

    @classmethod
    async def init_db(cls):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    performed_by TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """)

            await db.commit()

    @classmethod
    async def add_user(
        cls,
        username: str,
        password: str,
        role: Roles = "user",
        performed_by: str = "system",
    ):
        if await cls.get_user(username):
            raise ValueError(f"User {username} already exists.")

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )

            await cls.log_action(
                performed_by, "User created", f"Username: {username}, Role: {role}"
            )

            await db.commit()

    @classmethod
    async def get_user(cls, username: str):
        async with aiosqlite.connect(cls.db_path) as db:
            cursor = await db.execute(
                "SELECT username, password_hash, role FROM users WHERE username = ?",
                (username,),
            )

            return await cursor.fetchone()

    @classmethod
    async def add_token(cls, token: str, username: str, performed_by: str = "system"):
        token_hash = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                "INSERT INTO tokens (token_hash, username) VALUES (?, ?)",
                (token_hash, username),
            )

            await cls.log_action(
                performed_by, "Token added", f"Token added for username: {username}"
            )

            await db.commit()

    @classmethod
    async def get_username_by_token(cls, token: str):
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute("SELECT username, token_hash FROM tokens") as cursor:
                async for row in cursor:
                    username, token_hash = row
                    if bcrypt.checkpw(
                        token.encode("utf-8"), token_hash.encode("utf-8")
                    ):
                        return username

            return None

    @classmethod
    async def is_token_valid_for_user(cls, token: str, username: str) -> bool:
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                "SELECT token_hash FROM tokens WHERE username = ?", (username,)
            ) as cursor:
                async for row in cursor:
                    token_hash = row[0]
                    if bcrypt.checkpw(
                        token.encode("utf-8"), token_hash.encode("utf-8")
                    ):
                        return True

            return False

    @classmethod
    async def delete_token(cls, token: str, performed_by: str = "system"):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute("DELETE FROM tokens WHERE token_hash = ?", (token,))
            await cls.log_action(
                performed_by, "Token deleted", f"Token deleted: {token}"
            )

            await db.commit()

    @classmethod
    async def delete_token_by_username(
        cls, username: str, performed_by: str = "system"
    ):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute("DELETE FROM tokens WHERE username = ?", (username,))
            await cls.log_action(
                performed_by,
                "All tokens deleted",
                f"All tokens deleted for username: {username}",
            )

            await db.commit()

    @classmethod
    async def delete_user(cls, username: str, performed_by: str = "system"):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute("DELETE FROM users WHERE username = ?", (username,))
            await cls.log_action(
                performed_by, "User deleted", f"User deleted: {username}"
            )

            await db.commit()

    @classmethod
    async def login_user(
        cls, username: str, password: str, performed_by: str = "system"
    ) -> Optional[str]:
        user = await cls.get_user(username)
        if user is None:
            return None

        _, password_hash, _ = user
        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            return None

        token = str(uuid.uuid4())
        await cls.add_token(token, username, performed_by)

        return token

    @classmethod
    async def check_user_role(cls, username: str, required_role: Roles) -> bool:
        user = await cls.get_user(username)
        if user is None:
            return False

        _, _, role = user

        return role == required_role

    @classmethod
    async def log_action(
        cls, performed_by: str, action: str, details: Optional[str] = None
    ):
        async with aiosqlite.connect(cls.db_path) as db:
            await db.execute(
                "INSERT INTO audit_log (performed_by, action, details) VALUES (?, ?, ?)",
                (performed_by, action, details),
            )

            await db.commit()

    @classmethod
    async def get_audit_log(cls):
        async with aiosqlite.connect(cls.db_path) as db:
            async with db.execute(
                "SELECT performed_by, action, timestamp, details FROM audit_log ORDER BY timestamp DESC"
            ) as cursor:
                return await cursor.fetchall()
