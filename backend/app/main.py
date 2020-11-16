from fastapi import FastAPI
from . import models
from .api import login, users, services
from .database import engine

# TODO: tables shouldn't be created automatically
# -> use alembic
models.Base.metadata.create_all(bind=engine)

app = FastAPI()


app.include_router(login.router, prefix="/api/v1", tags=["login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["services"],
)
