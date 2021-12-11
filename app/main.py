import logging
import sentry_sdk
from pathlib import Path
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI
from fastapi.logger import logger
from fastapi.staticfiles import StaticFiles
from . import monitoring
from .api import login, users, services
from .views import exceptions, account, notifications, settings
from .settings import SENTRY_DSN, ESS_NOTIFY_SERVER_ENVIRONMENT


# The following logging setup assumes the app is run with gunicorn
gunicorn_error_logger = logging.getLogger("gunicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers
logger.handlers = gunicorn_error_logger.handlers
logger.setLevel(gunicorn_error_logger.level)

# Main application to serve HTML
app = FastAPI(exception_handlers=exceptions.exception_handlers)
app.include_router(account.router)
app.include_router(notifications.router, prefix="/notifications")
app.include_router(settings.router, prefix="/settings")

# Serve static files
app_dir = Path(__file__).parent.resolve()
app.mount("/static", StaticFiles(directory=str(app_dir / "static")), name="static")

# API mounted under /api
original_api = FastAPI()
original_api.include_router(monitoring.router, prefix="/-", tags=["monitoring"])
original_api.include_router(login.router, tags=["login"])
original_api.include_router(users.router, prefix="/users", tags=["users"])
original_api.include_router(
    services.router,
    prefix="/services",
    tags=["services"],
)

versioned_api = VersionedFastAPI(
    original_api,
    version_format="{major}",
    prefix_format="/v{major}",
)

app.mount("/api", versioned_api)

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ESS_NOTIFY_SERVER_ENVIRONMENT)
    app = SentryAsgiMiddleware(app)
