from fastapi import APIRouter

from hub_dbs.main_db import ServerManager

info_router = APIRouter(prefix='/api_v1/')


@info_router.get("/")
async def get_servers():
    return await ServerManager.get_all_active_servers()


@info_router.get("/ping")
async def ping():
    return {"message": "pong!"}
