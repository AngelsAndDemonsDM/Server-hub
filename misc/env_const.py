import os

from dotenv import load_dotenv

load_dotenv()

INIT_OWNER_PASSWORD = os.getenv("INIT_OWNER_PASSWORD", "owner_password")
