from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from . import deps
from .. import crud, models, schemas

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
