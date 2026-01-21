from fastapi import APIRouter, Depends, BackgroundTasks
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from fastapi.logger import logger
from . import templates
from .. import crud, deps, models, schemas, utils

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="settings")
async def settings_get(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    logger.info(f"Settings page accessed by user: {current_user.username}")

    try:
        services = crud.get_user_services(db, current_user)
        logger.info(
            f"Retrieved {len(services)} services for user {current_user.username}"
        )

        # Get filters for each service
        service_filters: dict[str, dict[str, str]] = {}
        for service in services:
            try:
                filter_record = crud.get_user_service_filter(
                    db, current_user.id, service.id
                )
                if filter_record:
                    # Convert model to dict for template
                    service_filters[str(service.id)] = {
                        "include_keywords": filter_record.include_keywords or "",
                        "exclude_keywords": filter_record.exclude_keywords or "",
                    }
                    logger.debug(
                        f"Loaded filter for service {service.id}: "
                        f"include={filter_record.include_keywords}, "
                        f"exclude={filter_record.exclude_keywords}"
                    )
                else:
                    # Create empty filter for services without filters
                    service_filters[str(service.id)] = {
                        "include_keywords": "",
                        "exclude_keywords": "",
                    }
            except Exception as e:
                logger.error(
                    f"Error getting filter for service {service.id}: {e}", exc_info=True
                )
                # Provide empty filter on error
                service_filters[str(service.id)] = {
                    "include_keywords": "",
                    "exclude_keywords": "",
                }

        logger.info(f"Rendering settings template with {len(service_filters)} filters")
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "current_user": current_user,
                "services": services,
                "service_filters": service_filters,
            },
        )
    except Exception as e:
        logger.error(
            f"CRITICAL: Settings page failed for user {current_user.username}: {e}",
            exc_info=True,
        )
        raise


@router.post("/", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user_from_session),
):
    form = await request.form()
    selected_categories = [key for key in form if not key.startswith("filter_")]

    services = crud.get_user_services(db, current_user)
    updated_services = []
    newly_subscribed_services = []

    for service in services:
        was_subscribed = service.is_subscribed
        is_now_subscribed = service.category in selected_categories

        service.is_subscribed = is_now_subscribed
        updated_services.append(
            schemas.UserUpdateService(
                id=service.id, is_subscribed=service.is_subscribed
            )
        )

        # Track newly subscribed services for backfill
        if not was_subscribed and is_now_subscribed:
            newly_subscribed_services.append(service)

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

    # Backfill notifications for newly subscribed services
    if newly_subscribed_services:
        background_tasks.add_task(
            utils.backfill_and_notify,
            current_user.id,
            [service.id for service in newly_subscribed_services],
        )

    # Redirect to prevent form resubmission
    return RedirectResponse(url="/settings", status_code=303)
