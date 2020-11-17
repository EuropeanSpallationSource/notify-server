from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/health")
def health_check():
    return PlainTextResponse("OK")
