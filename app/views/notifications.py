from fastapi import APIRouter, Depends
from starlette.responses import HTMLResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from . import templates
from .. import deps, models, crud

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="notifications")
async def notifications(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_cookie),
):
    services = crud.get_user_services(db, current_user)
    categories = {service.id: service.category for service in services}
    subscribed_services = [service for service in services if service.is_subscribed]
    notifications = crud.get_user_notifications(db, current_user)
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "current_user": current_user,
            "services": subscribed_services,
            "notifications": notifications,
            "categories": categories,
        },
    )
