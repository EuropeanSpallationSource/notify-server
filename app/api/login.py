from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.logger import logger
from sqlalchemy.orm import Session
from .. import deps, crud, utils, auth
from ..settings import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    if not auth.authenticate_user(form_data.username.lower(), form_data.password):
        logger.warning(f"Authentication failed for {form_data.username.lower()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    logger.info(f"User {form_data.username.lower()} successfully logged in")
    db_user = crud.get_user_by_username(db, form_data.username.lower())
    if db_user is None:
        db_user = crud.create_user(db, form_data.username.lower())
        response.status_code = status.HTTP_201_CREATED
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(db_user.username, expire=expire)
    crud.update_user_login_token_expire_date(db, db_user, expire)
    return {"access_token": access_token, "token_type": "bearer"}
