from typing import Optional

from fastapi import HTTPException


def validate_authorization(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    return authorization[len("Bearer ") :]
