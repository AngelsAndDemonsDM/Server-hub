from fastapi import HTTPException, Request

from .config import INIT_OWNER_PASSWORD, TIMEOUT_DURATION_MINUTES, USE_HTTPS
from .server_database import Database
from .user_database import UserDatabase


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = await UserDatabase.get_username_by_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if UserDatabase.check_user_role(user, "user"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user
