from fastapi import status
from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse
from starlette.requests import Request
from . import templates


async def not_authenticated(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")


async def bad_request(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "400.html",
        {"request": request, "detail": exc.detail},
        status_code=exc.status_code,
    )


async def forbidden(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "403.html", {"request": request}, status_code=exc.status_code
    )


async def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "404.html", {"request": request}, status_code=exc.status_code
    )


async def server_error(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


exception_handlers = {
    400: bad_request,
    401: not_authenticated,
    404: not_found,
    500: server_error,
}
