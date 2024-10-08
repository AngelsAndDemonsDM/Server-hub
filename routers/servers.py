import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from misc import get_current_user, server_db

servers_router = APIRouter()


class ServerModel(BaseModel):
    ip: str
    port: str
    name: str
    max_players: int
    cur_players: int
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    additional_links: Optional[dict] = None


class UpdateServerModel(BaseModel):
    token: str
    ip: Optional[str] = None
    port: Optional[str] = None
    max_players: Optional[int] = None
    cur_players: Optional[int] = None
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    additional_links: Optional[dict] = None


class AdminUpdateServerModel(BaseModel):
    ip: Optional[str] = None
    port: Optional[str] = None
    max_players: Optional[int] = None
    cur_players: Optional[int] = None
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    additional_links: Optional[dict] = None


# Добавление сервера
@servers_router.post("/servers/add")
async def add_server(server: ServerModel):
    try:
        token = secrets.token_hex(16)
        server_db.add_server(
            ip=server.ip,
            port=server.port,
            name=server.name,
            max_players=server.max_players,
            cur_players=server.cur_players,
            desc=server.desc,
            tags=server.tags,
            additional_links=server.additional_links,
        )
        server_db.set_ip_token(server.ip, token)
        return {"message": "Server added successfully", "token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Получение информации о сервере
@servers_router.get("/servers/{name}")
async def get_server(name: str):
    server = server_db.get_server(name)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    return server


# Обновление информации о сервере
@servers_router.put("/servers/{name}/update")
async def update_server(name: str, server: UpdateServerModel):
    try:
        existing_server = server_db.get_server(name)
        if existing_server is None:
            raise HTTPException(status_code=404, detail="Server not found")

        if server.token != server_db.get_ip_token(existing_server["ip"]):
            raise HTTPException(status_code=403, detail="Invalid token")

        server_db.update_server(
            name=name,
            ip=server.ip,
            port=server.port,
            max_players=server.max_players,
            cur_players=server.cur_players,
            desc=server.desc,
            tags=server.tags,
            additional_links=server.additional_links,
        )
        return {"message": "Server updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Получение списка серверов
@servers_router.get("/servers/all/")
async def list_servers():
    return server_db.list_servers()

# Для администраторов
# Обновление информации о сервере
@servers_router.put("/servers/admin/{name}/update")
async def admin_update_server(
    name: str,
    server: AdminUpdateServerModel,
    current_user: str = Depends(get_current_user),
):
    try:
        server_db.update_server(
            name=name,
            ip=server.ip,
            port=server.port,
            max_players=server.max_players,
            cur_players=server.cur_players,
            desc=server.desc,
            tags=server.tags,
            additional_links=server.additional_links,
        )
        return {"message": "Server updated successfully by admin"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Удаление сервера
@servers_router.delete("/servers/admin/{name}/remove")
async def remove_server(name: str, current_user: str = Depends(get_current_user)):
    try:
        server_db.remove_server(name)
        return {"message": "Server removed successfully"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Забанить IP-адрес
@servers_router.post("/servers/admin/ban_ip")
async def ban_ip(
    ip: str,
    duration: Optional[int] = None,
    reason: Optional[str] = "No reason provided",
    current_user: str = Depends(get_current_user),
):
    server_db.ban_ip(ip, duration, reason)
    return {"message": "IP banned successfully"}


# Разбанить IP-адрес
@servers_router.post("/servers/admin/unban_ip")
async def unban_ip(ip: str, current_user: str = Depends(get_current_user)):
    server_db.unban_ip(ip)
    return {"message": "IP unbanned successfully"}
