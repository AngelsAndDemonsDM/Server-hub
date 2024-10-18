import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

INIT_OWNER_PASSWORD = os.getenv("INIT_OWNER_PASSWORD", "owner_password")
TOKEN_EXPIRES_TIME = timedelta(hours=1)
