from fastapi import Depends, HTTPException, status
from starlette.requests import Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.logger import logger
from sqlalchemy.orm import Session
from jwt import PyJWTError, ExpiredSignatureError
from authlib.integrations.starlette_client import OAuth
from . import crud, models, utils
from .database import SessionLocal
from .settings import (
    OIDC_NAME,
    OIDC_SERVER_URL,
    OIDC_CLIENT_ID,
    OIDC_CLIENT_SECRET,
    OIDC_SCOPE,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
oauth = OAuth()
oauth.register(
    OIDC_NAME,
    client_id=OIDC_CLIENT_ID,
    client_secret=str(OIDC_CLIENT_SECRET),
    server_metadata_url=OIDC_SERVER_URL,
    client_kwargs={"scope": OIDC_SCOPE},
)


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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = utils.decode_access_token(token)
    except ExpiredSignatureError:
        msg = "Token has expired"
        logger.warning(msg)
        credentials_exception.detail = msg
        raise credentials_exception
    except PyJWTError as e:
        logger.warning(f"Error decoding JWT: {e}")
        raise credentials_exception
    username = payload.get("sub")
    if username is None:
        msg = "Missing subject claim in JWT"
        logger.warning(msg)
        credentials_exception.detail = msg
        raise credentials_exception
    user = crud.get_user_by_username(db, username)
    if user is None:
        msg = f"Unknown user {username}"
        logger.warning(msg)
        credentials_exception.detail = msg
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"User {username} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


def get_current_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Return the current user only if he is admin"""
    if not current_user.is_admin:
        logger.warning(f"User {current_user.username} doesn't have enough privileges")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_current_user_from_session(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication"
    )
    user_id = request.session.get("user_id")
    if user_id is None:
        raise unauthorized_exception
    user = crud.get_user(db, int(user_id))
    if user is None:
        logger.warning(f"Unknown user id {user_id}")
        raise unauthorized_exception
    if not user.is_active:
        logger.warning(f"User {user.username} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user
