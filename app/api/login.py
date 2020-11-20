from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.logger import logger
from sqlalchemy.orm import Session
from . import deps, ldap
from .. import crud

router = APIRouter()


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    if not ldap.authenticate_user(form_data.username, form_data.password):
        logger.warning(f"LDAP authentication failed for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    logger.info(f"User {form_data.username} successfully logged in")
    db_user = crud.get_user_by_username(db, form_data.username)
    if db_user is None:
        db_user = crud.create_user(db, form_data.username)
        response.status_code = status.HTTP_201_CREATED
    return {"access_token": db_user.token, "token_type": "bearer"}
