import json
import os

from dotenv import load_dotenv

load_dotenv()

INIT_OWNER_PASSWORD = os.getenv("INIT_OWNER_PASSWORD", "owner")

with open("config.json", "r") as file:
    _config = json.load(file)

HOST = _config.get("host", "0.0.0.0")
PORT = _config.get("port", 8000)
