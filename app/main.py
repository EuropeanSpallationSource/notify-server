import logging
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI
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

original_app = FastAPI()


original_app.include_router(monitoring.router, prefix="/-", tags=["monitoring"])
original_app.include_router(login.router, tags=["login"])
original_app.include_router(users.router, prefix="/users", tags=["users"])
original_app.include_router(
    services.router,
    prefix="/services",
    tags=["services"],
)

app = VersionedFastAPI(
    original_app,
    version_format="{major}",
    prefix_format="/api/v{major}",
)

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ESS_NOTIFY_SERVER_ENVIRONMENT)
    app = SentryAsgiMiddleware(app)
