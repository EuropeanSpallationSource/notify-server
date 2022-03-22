from fastapi.responses import Response
from itsdangerous.serializer import Serializer
from .settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, AUTH_COOKIE_NAME

serializer = Serializer(str(SECRET_KEY))


def set_auth(response: Response, user_id: int):
    val = serializer.dumps(user_id)
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
