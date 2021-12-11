from fastapi import APIRouter, Depends
from starlette.responses import HTMLResponse
from starlette.requests import Request
from . import templates
from .. import deps, models

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="notifications")
async def notifications(
    request: Request,
    current_user: models.User = Depends(deps.get_current_user_from_cookie),
):
    return templates.TemplateResponse(
        "notifications.html", {"request": request, "current_user": current_user}
    )
