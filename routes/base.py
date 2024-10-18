from fastapi import Header, HTTPException
from pydantic import BaseModel

from hub_dbs.main_db import ServerManager


class UserNamePassword(BaseModel):
    name: str
    password: str


def validate_auth_token(authorization: str = Header(...)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    return authorization[len("Bearer ") :]


async def auth_server(
    x_server_dns: str = Header(...), x_server_token: str = Header(...)
) -> str:
    server_info = await ServerManager.get_server_info(x_server_dns)
    if not server_info:
        raise HTTPException(status_code=404, detail="Server not found")

    token_hash = await ServerManager.get_api_token(x_server_dns)
    if not token_hash:
        raise HTTPException(status_code=401, detail="Token not found for server")

    if not ServerManager.verify_token(x_server_token, token_hash):
        raise HTTPException(status_code=401, detail="Invalid token")

    return x_server_dns
