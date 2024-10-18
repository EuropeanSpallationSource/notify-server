from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.logger import logger
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from . import templates
from .. import deps, crud, auth, models
from ..settings import APP_NAME, AUTHENTICATION_METHOD

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="index")
async def index(
    request: Request,
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    return RedirectResponse(url="/notifications")


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if AUTHENTICATION_METHOD == "oidc":
        redirect_uri = request.url_for("oidc_auth")
        return await deps.oauth.keycloak.authorize_redirect(request, redirect_uri)
    else:
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
    if AUTHENTICATION_METHOD == "oidc":
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Invalid method"
        )
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
    request.session["user_id"] = db_user.id
    return resp


@router.get("/auth")
async def oidc_auth(
    request: Request,
    db: Session = Depends(deps.get_db),
):
    token = await deps.oauth.keycloak.authorize_access_token(request)
    user_info = token["userinfo"]
    if user_info:
        username = user_info["preferred_username"].lower()
        db_user = crud.get_user_by_username(db, username)
        if db_user is None:
            db_user = crud.create_user(db, username)
        request.session["user_id"] = db_user.id
        return RedirectResponse(url=request.session.pop("next", "/"))
    return RedirectResponse(url="/login")


@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    request.session.pop("user_id", None)
    return response


@router.get("/privacy", response_class=HTMLResponse, name="privacy")
async def privacy(
    request: Request,
):
    return templates.TemplateResponse(
        "privacy_policy.html", {"request": request, "app_name": APP_NAME}
    )
