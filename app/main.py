from fastapi import FastAPI
from .api import login, users, services

app = FastAPI()


app.include_router(login.router, prefix="/api/v1", tags=["login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["services"],
)
