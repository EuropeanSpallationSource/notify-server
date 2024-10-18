from fastapi import APIRouter, Depends
from starlette.responses import HTMLResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from . import templates
from .. import crud, deps, models, schemas

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="settings")
async def settings_get(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    services = crud.get_user_services(db, current_user)
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "current_user": current_user, "services": services},
    )


@router.post("/", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    form = await request.form()
    selected_categories = list(form.keys())
    services = crud.get_user_services(db, current_user)
    updated_services = []
    for service in services:
        if service.category in selected_categories:
            service.is_subscribed = True
        else:
            service.is_subscribed = False
        updated_services.append(
            schemas.UserUpdateService(
                id=service.id, is_subscribed=service.is_subscribed
            )
        )
    crud.update_user_services(db, updated_services, current_user)
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "current_user": current_user, "services": services},
    )
