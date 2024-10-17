from typing import Optional

from fastapi import APIRouter, Body, Header, HTTPException

from hub_dbs.main_db import BanError, UserAlreadyExistsError, UserManager

from .base import validate_authorization

user_router = APIRouter(prefix="/api_v1/user")


@user_router.post("/register")
async def register(username: str = Body(...), password: str = Body(...)):
    try:
        token = await UserManager.register(username, password)

    except UserAlreadyExistsError as err:
        raise HTTPException(400, str(err))

    except Exception as err:
        raise HTTPException(500, str(err))

    return {"message": "Register successful", "token": token}


@user_router.post("/login")
async def login(username: str = Body(...), password: str = Body(...)):
    try:
        token = await UserManager.login(username, password)

    except BanError as err:
        raise HTTPException(403, str(err))

    except ValueError as err:
        raise HTTPException(401, str(err))

    except Exception as err:
        raise HTTPException(500, str(err))

    return {"message": "Login successful", "token": token}


@user_router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None), full_logout: bool = False
):
    token = validate_authorization(authorization)

    try:
        if full_logout:
            await UserManager.full_logout(token)
        else:
            await UserManager.logout(token)

    except ValueError as err:
        raise HTTPException(401, str(err))

    except Exception as err:
        raise HTTPException(500, str(err))

    return {"message": "Logout successful"}
