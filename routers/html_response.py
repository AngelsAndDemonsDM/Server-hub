from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from misc import get_current_user, user_db

html_response_router = APIRouter()


@html_response_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    if token and user_db.get_username_by_token(token):
        return RedirectResponse(url="/admin", status_code=302)

    with open("html/login.html", "r", encoding='utf-8') as file:
        html_content = file.read()

    return HTMLResponse(content=html_content)


@html_response_router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel(current_user: str = Depends(get_current_user)):
    with open("html/admin_panel.html", "r", encoding='utf-8') as file:
        html_content = file.read()

    return HTMLResponse(content=html_content)
