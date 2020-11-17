import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import FastAPI
from .api import login, users, services
from .settings import SENTRY_DSN

app = FastAPI()


app.include_router(login.router, prefix="/api/v1", tags=["login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["services"],
)

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN)
    app = SentryAsgiMiddleware(app)
