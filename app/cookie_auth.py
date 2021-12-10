import hashlib
import hmac
from fastapi.responses import Response
from .settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, AUTH_COOKIE_NAME

AUTH_SIZE = 16


def sign(cookie: str) -> str:
    h = hashlib.blake2b(digest_size=AUTH_SIZE, key=str(SECRET_KEY).encode("utf-8"))
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


def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME)
