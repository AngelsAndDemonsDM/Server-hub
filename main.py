from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from hub_dbs import Database, LogsDatabase, RoleManager, UserManager
from routes import connect_router, info_router, server_router, user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("dbs").mkdir(parents=True, exist_ok=True)
    await LogsDatabase.init_db()
    await Database.init_tables()
    await RoleManager.init_manager()
    await UserManager.init_manager()
    yield
    return


app = FastAPI(lifespan=lifespan, title="Server hub api")
app.include_router(connect_router)
app.include_router(info_router)
app.include_router(server_router)
app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run(app)
