import uvicorn
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles

from misc import HOST, PORT
from routers import auth_router, html_response_router

app = FastAPI()

app.mount("/style", StaticFiles(directory="style"), name="style")
app.mount("/html", StaticFiles(directory="html"), name="html")

app.include_router(auth_router)
app.include_router(html_response_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
