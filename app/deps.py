from fastapi import Depends, HTTPException, status
from starlette.requests import Request
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from fastapi.logger import logger
from itsdangerous.exc import BadSignature
from sqlalchemy.orm import Session
from jwt import PyJWTError, ExpiredSignatureError
from . import crud, models, utils, cookie_auth
from .database import SessionLocal
from .settings import AUTH_COOKIE_NAME

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
cookie_sec = APIKeyCookie(name=AUTH_COOKIE_NAME)


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


def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication"
    )
    if AUTH_COOKIE_NAME not in request.cookies:
        raise unauthorized_exception
    cookie = request.cookies[AUTH_COOKIE_NAME]
    try:
        user_id = cookie_auth.serializer.loads(cookie)
    except BadSignature as e:
        logger.warning(f"Bad Signature, invalid cookie value: {e}")
        raise unauthorized_exception
    user = crud.get_user(db, user_id)
    if user is None:
        logger.warning(f"Unknown user id {user_id}")
        raise unauthorized_exception
    if not user.is_active:
        logger.warning(f"User {user.username} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user
