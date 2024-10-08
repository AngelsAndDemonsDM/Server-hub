import json
import os

from dotenv import load_dotenv

load_dotenv()

INIT_OWNER_PASSWORD = os.getenv("INIT_OWNER_PASSWORD", "owner")

with open("config.json", "r") as file:
    _config = json.load(file)

MAX_SERVERS_PER_IP = _config.get("max_servers_per_ip", 3)
TIMEOUT_DURATION_MINUTES = _config.get("timeout_duration_minutes", 5)
HOST = _config.get("host", "0.0.0.0")
PORT = _config.get("port", 8000)
