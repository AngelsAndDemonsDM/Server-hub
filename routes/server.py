from fastapi import APIRouter, Depends

from hub_dbs.main_db import ServerManager

from .base import auth_server

server_router = APIRouter(prefix="/api_v1/server")


@server_router.post("/update_status")
async def update_status(
    status: ServerManager.StatusType, dns_name: str = Depends(auth_server)
):
    await ServerManager.update_server_status(dns_name, status)
    return {"message": "success"}


@server_router.post("/update_players")
async def update_players(count: int, dns_name: str = Depends(auth_server)):
    await ServerManager.update_server_players(dns_name, count)
    return {"message": "success"}
