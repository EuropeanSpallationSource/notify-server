from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from . import crud, models, schemas, ldap
from .database import SessionLocal, engine

# TODO: tables shouldn't be created automatically
# -> use alembic
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    """Return the current user based on the bearer token from the header"""
    user = crud.get_user_by_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user


def get_current_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Return the current user only if he is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


@app.post("/login")
def login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends(),
):
    if not ldap.authenticate_user(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    db_user = crud.get_user_by_username(db, form_data.username)
    if db_user is None:
        db_user = crud.create_user(db, form_data.username)
    return {"access_token": db_user.token, "token_type": "bearer"}


@app.get("/user/profile", response_model=schemas.User)
def read_user_profile(current_user: models.User = Depends(get_current_user)):
    """Return the current user profile"""
    return current_user


@app.post(
    "/user/apn-token", response_model=schemas.User, status_code=status.HTTP_201_CREATED
)
def create_user_apn_token(
    response: Response,
    apn_token: schemas.ApnToken,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create or update an apn token"""
    if apn_token.apn_token in current_user.apn_tokens:
        response.status_code = status.HTTP_200_OK
        return current_user
    return crud.create_user_apn_token(db, apn_token.apn_token, current_user)


@app.get("/user/services/", response_model=List[schemas.UserService])
def read_user_services(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return crud.get_user_services(db, current_user)


@app.patch("/user/services/")
def update_user_services(
    updated_services: List[schemas.UserUpdateService],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.update_user_services(db, updated_services, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/user/notifications/", response_model=List[schemas.UserNotification])
def read_user_notifications(current_user: models.User = Depends(get_current_user)):
    return crud.get_user_notifications(current_user)


@app.patch("/user/notifications/")
def update_user_notifications(
    updated_notifications: List[schemas.UserUpdateNotification],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.update_user_notifications(db, updated_notifications, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/services/", response_model=schemas.Service)
def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Create a new service"""
    db_service = crud.create_service(db, service=service)
    return db_service


@app.get("/services/", response_model=List[schemas.Service])
def list_services(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    db_services = crud.get_services(db)
    return db_services
