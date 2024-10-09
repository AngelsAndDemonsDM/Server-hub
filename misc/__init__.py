from fastapi import HTTPException, Request

from .config import (HOST, INIT_OWNER_PASSWORD, PORT,  # noqa: F401
                     TIMEOUT_DURATION_MINUTES, USE_HTTPS)
from .server_database import ServerDatabase
from .user_database import UserDatabase

user_db = UserDatabase()
server_db = ServerDatabase()
server_db.TIMEOUT_DURATION_MINUTES = TIMEOUT_DURATION_MINUTES

if not user_db.get_user("owner"):
    user_db.add_user("owner", INIT_OWNER_PASSWORD)


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = user_db.get_username_by_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return user
