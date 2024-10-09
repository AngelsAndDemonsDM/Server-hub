import json
import os

from dotenv import load_dotenv

load_dotenv()

INIT_OWNER_PASSWORD = os.getenv("INIT_OWNER_PASSWORD", "owner")

try:
    with open("config.json", "r", encoding="utf-8") as file:
        _config = json.load(file)
except Exception:
    _config = {}

USE_HTTPS = _config.get("use_https", True)
MAX_SERVERS_PER_IP = _config.get("max_servers_per_ip", 3)
TIMEOUT_DURATION_MINUTES = _config.get("timeout_duration_minutes", 5)
