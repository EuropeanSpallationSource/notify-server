import hashlib
import hmac
from typing import Optional
from fastapi.logger import logger
from fastapi.requests import Request
from fastapi.responses import Response
from .settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

AUTH_COOKIE_NAME = "notify_token"
AUTH_SIZE = 16


def sign(cookie: str) -> str:
    h = hashlib.blake2b(digest_size=AUTH_SIZE, key=SECRET_KEY)
    h.update(cookie.encode("utf-8"))
    return h.hexdigest()


def verify(cookie: str, sig: str) -> bool:
    good_sig = sign(cookie)
    return hmac.compare_digest(good_sig, sig)


def set_auth(response: Response, user_id: int):
    sig = sign(str(user_id))
    val = f"{user_id}:{sig}"
    response.set_cookie(
        AUTH_COOKIE_NAME,
        val,
        secure=False,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="Lax",
    )


def get_user_id_via_auth_cookie(request: Request) -> Optional[int]:
    if AUTH_COOKIE_NAME not in request.cookies:
        return None
    val = request.cookies[AUTH_COOKIE_NAME]
    parts = val.split(":")
    if len(parts) != 2:
        return None
    user_id, sig = parts
    if not verify(str(user_id), sig):
        logger.warning("Hash mismatch, invalid cookie value")
        return None
    try:
        return int(user_id)
    except ValueError:
        logger.warning(f"Invalid user_id {user_id} in cookie")
        return None


def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME)
