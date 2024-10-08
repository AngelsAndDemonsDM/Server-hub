import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class ServerDatabase:
    TIMEOUT_DURATION_MINUTES = 5

    def __init__(self, db_path="banlist.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

        self._servers: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, datetime] = {}
        self._ip_count: Dict[str, int] = {}
        self._ip_token: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()

    def _create_tables(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS banned_ips (
                                ip TEXT PRIMARY KEY,
                                banned_at TIMESTAMP,
                                ban_duration INTEGER
                              )""")
        self.conn.commit()

    def is_ip_banned(self, ip: str) -> bool:
        cursor = self.conn.execute(
            "SELECT banned_at, ban_duration FROM banned_ips WHERE ip = ?", (ip,)
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            banned_at, ban_duration = row
            if ban_duration is None:
                return True  # Permanent ban
            if datetime.now(timezone.utc) < datetime.fromisoformat(
                banned_at
            ) + timedelta(seconds=ban_duration):
                return True
            else:
                self.unban_ip(ip)  # Remove expired ban

        return False

    def ban_ip(self, ip: str, duration: Optional[int] = None) -> None:
        self.conn.execute(
            "REPLACE INTO banned_ips (ip, banned_at, ban_duration) VALUES (?, ?, ?)",
            (ip, datetime.now(timezone.utc).isoformat(), duration),
        )
        self.conn.commit()

    def unban_ip(self, ip: str) -> None:
        self.conn.execute("DELETE FROM banned_ips WHERE ip = ?", (ip,))
        self.conn.commit()

    def add_server(
        self,
        ip: str,
        port: str,
        name: str,
        max_players: int,
        cur_players: int,
        desc: Optional[str] = None,
        tags: Optional[List[str]] = None,
        additional_links: Optional[Dict[str, str]] = None,
    ) -> None:
        with self._lock:
            if self.is_ip_banned(ip):
                raise ValueError(f"IP {ip} is banned from adding servers")

            if self._ip_count.get(ip, 0) >= 3:
                raise ValueError(f"IP {ip} has reached the limit of 3 servers")

            if name in self._servers:
                raise ValueError(f"{name} already in server list")

            self._servers[name] = {
                "ip": ip,
                "port": port,
                "max_players": max_players,
                "cur_players": cur_players,
                "desc": desc,
                "tags": tags if tags else [],
                "additional_links": additional_links if additional_links else {},
            }
            self._last_update[name] = datetime.now(timezone.utc)
            self._ip_count[ip] = self._ip_count.get(ip, 0) + 1

    def remove_server(self, name: str) -> None:
        with self._lock:
            if name not in self._servers:
                raise ValueError(f"{name} not found in server list")
            ip = self._servers[name]["ip"]
            del self._servers[name]
            del self._last_update[name]
            self._ip_count[ip] -= 1
            if self._ip_count[ip] == 0:
                del self._ip_count[ip]

    def update_server(
        self,
        name: str,
        ip: Optional[str] = None,
        port: Optional[str] = None,
        max_players: Optional[int] = None,
        cur_players: Optional[int] = None,
        desc: Optional[str] = None,
        tags: Optional[List[str]] = None,
        additional_links: Optional[Dict[str, str]] = None,
    ) -> None:
        with self._lock:
            if name not in self._servers:
                raise ValueError(f"{name} not found in server list")

            server = self._servers[name]

            if ip is not None:
                server["ip"] = ip
            if port is not None:
                server["port"] = port
            if max_players is not None:
                server["max_players"] = max_players
            if cur_players is not None:
                server["cur_players"] = cur_players
            if desc is not None:
                server["desc"] = desc
            if tags is not None:
                server["tags"] = tags
            if additional_links is not None:
                server["additional_links"] = additional_links

            self._last_update[name] = datetime.now(timezone.utc)

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._servers.get(name, None)

    def list_servers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"name": name, **data}
                for name, data in sorted(
                    self._servers.items(),
                    key=lambda x: x[1]["cur_players"],
                    reverse=True,
                )
            ]

    def remove_inactive_servers(self) -> None:
        with self._lock:
            now = datetime.now(timezone.utc)
            inactive_servers = [
                name
                for name, last_update in self._last_update.items()
                if now - last_update > timedelta(minutes=self.TIMEOUT_DURATION_MINUTES)
            ]
            for name in inactive_servers:
                del self._servers[name]
                del self._last_update[name]

    def _start_cleanup_thread(self) -> None:
        cleanup_thread = threading.Thread(
            target=self._cleanup_inactive_servers, daemon=True
        )
        cleanup_thread.start()

    def _cleanup_inactive_servers(self) -> None:
        while True:
            self.remove_inactive_servers()
            threading.Event().wait(60)

    # Token management methods for admin use
    def set_ip_token(self, ip: str, token: str) -> None:
        with self._lock:
            self._ip_token[ip] = token

    def get_ip_token(self, ip: str) -> Optional[str]:
        with self._lock:
            return self._ip_token.get(ip)

    def remove_ip_token(self, ip: str) -> None:
        with self._lock:
            if ip in self._ip_token:
                del self._ip_token[ip]
