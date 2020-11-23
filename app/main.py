import logging
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import FastAPI
from fastapi.logger import logger
from . import monitoring
from .api import login, users, services
from .settings import SENTRY_DSN, ESS_NOTIFY_SERVER_ENVIRONMENT


# The following logging setup assumes the app is run with gunicorn
gunicorn_error_logger = logging.getLogger("gunicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers
logger.handlers = gunicorn_error_logger.handlers
logger.setLevel(gunicorn_error_logger.level)

app = FastAPI()


app.include_router(monitoring.router, prefix="/-", tags=["monitoring"])
app.include_router(login.router, prefix="/api/v1", tags=["login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["services"],
)

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ESS_NOTIFY_SERVER_ENVIRONMENT)
    app = SentryAsgiMiddleware(app)
