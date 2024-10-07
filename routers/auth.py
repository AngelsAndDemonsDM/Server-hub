import secrets

import bcrypt
from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse

from misc import get_current_user, user_db

auth_router = APIRouter()


@auth_router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = user_db.get_user(username)
    if not user:
        return JSONResponse(
            status_code=400, content={"error": "Incorrect username or password"}
        )
    username, password_hash = user
    
    if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
        return JSONResponse(
            status_code=400, content={"error": "Incorrect username or password"}
        )

    token = secrets.token_hex(16)
    user_db.add_token(token, username)
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie(
        key="access_token", value=token, secure=True, httponly=True, samesite="strict"
    )
    return response


@auth_router.get("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    user_db.delete_token_by_username(current_user)

    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response