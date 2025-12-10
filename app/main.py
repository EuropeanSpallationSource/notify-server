import contextlib
import logging
import httpx
import jwt
import sentry_sdk
from pathlib import Path
from typing import AsyncIterator, TypedDict
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import FastAPI
from ._vendor.fastapi_versioning import VersionedFastAPI
from fastapi.logger import logger
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from . import monitoring, schemas
from .api import login, users, services
from .views import exceptions, account, notifications, settings, docs
from .settings import (
    SENTRY_DSN,
    ESS_NOTIFY_SERVER_ENVIRONMENT,
    SECRET_KEY,
    SESSION_MAX_AGE,
    OIDC_BASE_URL,
    OIDC_ENABLED,
)


# The following logging setup assumes the app is run with gunicorn
gunicorn_error_logger = logging.getLogger("gunicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers
logger.handlers = gunicorn_error_logger.handlers
logger.setLevel(gunicorn_error_logger.level)


class State(TypedDict):
    oidc_config: dict[schemas.RealmType, dict[str, str]]
    jwks_client: dict[schemas.RealmType, jwt.PyJWKClient] | None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    oidc_config = {}
    jwks_client = {}
    if OIDC_ENABLED:
        async with httpx.AsyncClient() as client:
            for realm in schemas.RealmType:
                url = f"{OIDC_BASE_URL}/realms/{login.discover_realm(realm)}/.well-known/openid-configuration"
                r = await client.get(url)
                if r.status_code == 200:
                    oidc_config[realm] = r.json()
                    jwks_uri = oidc_config[realm]["jwks_uri"]
                    jwks_client[realm] = jwt.PyJWKClient(jwks_uri)
    yield {"oidc_config": oidc_config, "jwks_client": jwks_client}


# Main application to serve HTML
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        session_cookie="notify_session",
        max_age=SESSION_MAX_AGE,
        same_site="strict",
        https_only=True,
    )
]
app = FastAPI(
    exception_handlers=exceptions.exception_handlers,
    middleware=middleware,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.include_router(account.router)
app.include_router(notifications.router, prefix="/notifications")
app.include_router(settings.router, prefix="/settings")
app.include_router(docs.router)


# Serve static files
app_dir = Path(__file__).parent.resolve()
app.mount("/static", StaticFiles(directory=str(app_dir / "static")), name="static")

# API mounted under /api
original_api = FastAPI(docs_url=None, redoc_url=None)
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
    docs_url=None,
    redoc_url=None,
)

app.mount("/api", versioned_api)


if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ESS_NOTIFY_SERVER_ENVIRONMENT)
    app = SentryAsgiMiddleware(app)
