from fastapi import APIRouter, Depends, status
from fastapi.logger import logger
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from . import templates
from .. import cookie_auth, crud, auth
from ..api import deps

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "username": "",
            "password": "",
            "error": "",
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    db: Session = Depends(deps.get_db),
):
    form = await request.form()
    username = form.get("username", "").lower().strip()
    password = form.get("password", "").strip()
    result = {
        "request": request,
        "username": username,
        "password": password,
        "error": "",
    }

    if not username or not password:
        result["error"] = "You must specify a username and password"
        return templates.TemplateResponse("login.html", result)
    if not auth.authenticate_user(username, password):
        logger.warning(f"Authentication failed for {username}")
        result["error"] = "Invalid Username/Password"
        return templates.TemplateResponse("login.html", result)
    logger.info(f"User {username} successfully logged in")
    db_user = crud.get_user_by_username(db, username.lower())
    if db_user is None:
        db_user = crud.create_user(db, username.lower())

    resp = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    cookie_auth.set_auth(resp, db_user.id)
    return resp


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    cookie_auth.logout(response)
    return response
