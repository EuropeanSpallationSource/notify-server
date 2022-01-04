from fastapi import APIRouter, Depends
from starlette.responses import HTMLResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from . import templates
from .. import deps, models, crud, schemas

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="notifications")
async def notifications_get(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_cookie),
):
    services = crud.get_user_services(db, current_user)
    categories = {service.id: service.category for service in services}
    selected_services = [
        schemas.UserServiceForm.from_user_service(service)
        for service in services
        if service.is_subscribed
    ]
    notifications = crud.get_user_notifications(db, current_user)
    request.session["selected_categories"] = [
        service.category for service in selected_services
    ]
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "current_user": current_user,
            "services": selected_services,
            "notifications": notifications,
            "categories": categories,
        },
    )


@router.post("/", response_class=HTMLResponse, name="notifications")
async def notifications_post(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_cookie),
):
    form = await request.form()
    selected_categories = list(form.keys())
    request.session["selected_categories"] = selected_categories
    user_services = crud.get_user_services(db, current_user)
    selected_services = [
        schemas.UserServiceForm.from_user_service(service)
        for service in user_services
        if service.is_subscribed
    ]
    for service in selected_services:
        if service.category in selected_categories:
            service.is_selected = True
        else:
            service.is_selected = False
    categories = {service.id: service.category for service in user_services}
    selected_services_id = [
        service.id
        for service in user_services
        if service.category in selected_categories
    ]
    notifications = crud.get_user_notifications(
        db, current_user, filter_services_id=selected_services_id
    )
    return templates.TemplateResponse(
        "notifications_table_form.html",
        {
            "request": request,
            "services": selected_services,
            "notifications": notifications,
            "categories": categories,
        },
    )


@router.get("/update", response_class=HTMLResponse, name="notifications")
async def notifications_update(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_cookie),
):
    user_services = crud.get_user_services(db, current_user)
    categories = {service.id: service.category for service in user_services}
    selected_categories = request.session.get("selected_categories", [])
    selected_services_id = [
        service.id
        for service in user_services
        if service.category in selected_categories
    ]
    notifications = crud.get_user_notifications(
        db, current_user, filter_services_id=selected_services_id
    )
    return templates.TemplateResponse(
        "notifications_table.html",
        {
            "request": request,
            "notifications": notifications,
            "categories": categories,
        },
    )
