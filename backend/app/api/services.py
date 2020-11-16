import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import deps
from .. import crud, models, schemas, tasks

router = APIRouter()


@router.get("/", response_model=List[schemas.Service])
def read_services(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Read all services"""
    db_services = crud.get_services(db)
    return db_services


@router.post("/", response_model=schemas.Service)
def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Create a new service"""
    db_service = crud.create_service(db, service=service)
    return db_service


@router.post("/{service_id}/notifications", response_model=schemas.Notification)
def create_notification_for_service(
    service_id: uuid.UUID,
    notification: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
):
    """Create a notification for the given service"""
    db_service = crud.get_service(db, service_id)
    if db_service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    db_notification = crud.create_service_notification(
        db=db, notification=notification, service=db_service
    )
    # Send notification using background task
    background_tasks.add_task(tasks.send_notification, db_notification)
    return db_notification
