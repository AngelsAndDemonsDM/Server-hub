from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from hub_dbs import Database, LogsDatabase, RoleManager, UserManager
from routes import user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("dbs").mkdir(parents=True, exist_ok=True)
    await LogsDatabase.init_db()
    await Database.init_tables()
    await RoleManager.init_manager()
    await UserManager.init_manager()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run(app)
