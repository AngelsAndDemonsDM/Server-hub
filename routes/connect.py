from fastapi import APIRouter, HTTPException

from hub_dbs.main_db import ClusterManager, ServerManager

connect_router = APIRouter(prefix="/api_v1/connect")


@connect_router.get("/{full_path}", tags=["connect api"])
async def connect(full_path: str):
    try:
        type_connect, name = full_path.split(".")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'type.name'.")

    result = None
    if type_connect == "cluster":
        result = await ClusterManager.get_least_loaded_server(name)

    elif type_connect == "single":
        result = await ServerManager.get_server_info(name)

    if result is None:
        raise HTTPException(status_code=404, detail=f"{type_connect}.{name} not found")

    return result
