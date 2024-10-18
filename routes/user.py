from fastapi import APIRouter, Depends, HTTPException

from hub_dbs.main_db import BanError, UserAlreadyExistsError, UserManager

from .base import UserNamePassword, auth_user

user_router = APIRouter(prefix="/api_v1/user")


@user_router.post("/register", tags=["user api"])
async def register(user: UserNamePassword):
    try:
        token = await UserManager.register(user.name, user.password)

    except UserAlreadyExistsError as err:
        raise HTTPException(400, str(err))

    except Exception as err:
        raise HTTPException(500, str(err))

    return {"message": "Register successful", "token": token}


@user_router.post("/login", tags=["user api"])
async def login(user: UserNamePassword):
    try:
        token = await UserManager.login(user.name, user.password)

    except BanError as err:
        raise HTTPException(403, str(err))

    except ValueError as err:
        raise HTTPException(401, str(err))

    except Exception as err:
        raise HTTPException(500, str(err))

    return {"message": "Login successful", "token": token}


@user_router.post("/logout", tags=["user api"])
async def logout(user_name: str = Depends(auth_user)):
    await UserManager.logout(user_name)
    return {"message": "Logout successful"}
