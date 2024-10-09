import uvicorn
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles

from routers import auth_router, html_response_router, servers_router

app = FastAPI(title="Server hub", description="", version="0.0.1")

app.mount("/style", StaticFiles(directory="style"), name="style")
app.mount("/html", StaticFiles(directory="html"), name="html")

app.include_router(auth_router)
app.include_router(html_response_router)
app.include_router(servers_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if __name__ == "__main__":
    uvicorn.run(app)
