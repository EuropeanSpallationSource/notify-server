import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request, status
from fastapi.logger import logger
from sqlalchemy.orm import Session
from typing import List
from . import deps
from .. import crud, models, schemas, utils

router = APIRouter()


@router.get("/", response_model=List[schemas.Service])
def read_services(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Read all services"""
    db_services = crud.get_services(db)
    return db_services


@router.post("/", response_model=schemas.Service, status_code=status.HTTP_201_CREATED)
def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Create a new service - admin only"""
    db_service = crud.create_service(db, service=service)
    return db_service


@router.get("/{service_id}/notifications", response_model=List[schemas.Notification])
def read_service_notifications(
    service_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Read the service notifications - admin only"""
    db_service = crud.get_service(db, service_id)
    if db_service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    return db_service.notifications


@router.post(
    "/{service_id}/notifications",
    response_model=schemas.Notification,
    status_code=status.HTTP_201_CREATED,
)
def create_notification_for_service(
    request: Request,
    service_id: uuid.UUID,
    notification: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
):
    """Create a notification for the given service"""
    ip = request.client.host
    if not utils.is_ip_allowed(ip):
        logger.warning(f"IP {ip} not allowed to create a notification!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="IP address not allowed"
        )
    db_service = crud.get_service(db, service_id)
    if db_service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    db_notification = crud.create_service_notification(
        db=db, notification=notification, service=db_service
    )
    # Send notification using background task
    background_tasks.add_task(utils.send_notification, db_notification)
    return db_notification
