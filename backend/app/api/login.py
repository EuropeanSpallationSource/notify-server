from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import deps, ldap
from .. import crud

router = APIRouter()


@router.post("/login")
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    if not ldap.authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    db_user = crud.get_user_by_username(db, form_data.username)
    if db_user is None:
        db_user = crud.create_user(db, form_data.username)
    return {"access_token": db_user.token, "token_type": "bearer"}
