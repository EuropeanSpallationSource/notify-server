from fastapi import APIRouter, Depends, Form
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Optional
from . import templates
from .. import crud, deps, models, schemas
import uuid

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="settings")
async def settings_get(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    services = crud.get_user_services(db, current_user)
    
    # Get filters for each service
    service_filters = {}
    for service in services:
        filter_record = crud.get_user_service_filter(db, current_user.id, service.id)
        if filter_record:
            service_filters[str(service.id)] = filter_record
        else:
            # Create empty filter object if none exists
            service_filters[str(service.id)] = schemas.UserServiceFilter(
                include_keywords="", exclude_keywords=""
            )
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": current_user,
            "services": services,
            "service_filters": service_filters,
        },
    )


@router.post("/", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    form = await request.form()
    selected_categories = [key for key in form.keys() if not key.startswith('filter_')]
    
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
        
        # Update filters for this service
        service_id_str = str(service.id)
        include_key = f"filter_include_{service_id_str}"
        exclude_key = f"filter_exclude_{service_id_str}"
        
        if include_key in form or exclude_key in form:
            include_keywords = form.get(include_key, "")
            exclude_keywords = form.get(exclude_key, "")
            
            filter_update = schemas.UserServiceFilterUpdate(
                include_keywords=include_keywords,
                exclude_keywords=exclude_keywords,
            )
            crud.create_or_update_user_service_filter(
                db, current_user, service.id, filter_update
            )
    
    crud.update_user_services(db, updated_services, current_user)
    
    # Redirect to prevent form resubmission
    return RedirectResponse(url="/settings", status_code=303)
