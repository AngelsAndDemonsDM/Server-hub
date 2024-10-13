from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from hub_dbs import Database, LogsDatabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("dbs").mkdir(parents=True, exist_ok=True)
    await LogsDatabase.init_db()
    await Database.init_db()
    yield


app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run(app)
