import sqlite3

import bcrypt


class UserDatabase:
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
            cursor = self.conn.execute("SELECT username, token_hash FROM tokens")
            for row in cursor.fetchall():
                username, token_hash = row
                if bcrypt.checkpw(token.encode("utf-8"), token_hash):
                    return username
            return None


    def delete_token(self, token):
        with self.conn:
            self.conn.execute("DELETE FROM tokens WHERE token_hash = ?", (token,))

    def delete_token_by_username(self, username):
        with self.conn:
            self.conn.execute("DELETE FROM tokens WHERE username = ?", (username,))
