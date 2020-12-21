from fastapi import APIRouter, Depends, Response, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import deps
from .. import crud, models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Return all users - admin only"""
    users = crud.get_users(db)
    return users


@router.patch("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    updated_info: schemas.UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Update the given user - admin only"""
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    updated_user = crud.update_user(db, user, updated_info)
    return updated_user


@router.delete("/{user_id}", response_model=schemas.User)
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    """Update the given user - admin only"""
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    crud.delete_user(db, user)


@router.get("/user/profile", response_model=schemas.User)
def read_current_user_profile(
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return the current user profile"""
    return current_user


@router.post(
    "/user/apn-token", response_model=schemas.User, status_code=status.HTTP_201_CREATED
)
def create_current_user_apn_token(
    response: Response,
    apn_token: schemas.ApnToken,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Create or update an apn token for the current user"""
    if apn_token.apn_token in current_user.apn_tokens:
        response.status_code = status.HTTP_200_OK
        return current_user
    return crud.create_user_apn_token(db, apn_token.apn_token, current_user)


@router.get("/user/services", response_model=List[schemas.UserService])
def read_current_user_services(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Read the current user's services"""
    return crud.get_user_services(db, current_user)


@router.patch("/user/services", status_code=status.HTTP_204_NO_CONTENT)
def update_current_user_services(
    updated_services: List[schemas.UserUpdateService],
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Update the current user's services"""
    crud.update_user_services(db, updated_services, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/user/notifications", response_model=List[schemas.UserNotification])
def read_current_user_notifications(
    current_user: models.User = Depends(deps.get_current_user),
):
    """Read the current user's notifications"""
    return crud.get_user_notifications(current_user)


@router.patch("/user/notifications", status_code=status.HTTP_204_NO_CONTENT)
def update_current_user_notifications(
    updated_notifications: List[schemas.UserUpdateNotification],
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Update the current user's notifications"""
    crud.update_user_notifications(db, updated_notifications, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
