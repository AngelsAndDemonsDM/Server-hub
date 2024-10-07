import sqlite3

import bcrypt
from fastapi import HTTPException, Request

from .config import INIT_OWNER_PASSWORD


class _user_database:
    def __init__(self, db_path="user.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)

    def add_user(self, username, password):
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )

    def get_user(self, username):
        with self.conn:
            return self.conn.execute(
                "SELECT username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

    def add_token(self, token, username):
        token_hash = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt())
        with self.conn:
            self.conn.execute(
                "INSERT INTO tokens (token_hash, username) VALUES (?, ?)",
                (token_hash, username),
            )

    def get_username_by_token(self, token):
        with self.conn:
            cursor = self.conn.execute(
                "SELECT username FROM tokens WHERE token_hash = ?", (token,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def delete_token(self, token):
        with self.conn:
            self.conn.execute("DELETE FROM tokens WHERE token_hash = ?", (token,))

    def delete_token_by_username(self, username):
        with self.conn:
            self.conn.execute("DELETE FROM tokens WHERE username = ?", (username,))


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    username = user_db.get_username_by_token(token)
    if not token or not username:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )
    return username


user_db = _user_database()

if not user_db.get_user("owner"):
    user_db.add_user("owner", INIT_OWNER_PASSWORD)
