import pytest
from fastapi.testclient import TestClient
from starlette.config import environ
from sqlalchemy.orm import sessionmaker
from pytest_factoryboy import register
from typing import Generator

# Overwrite default settings.
# Note that those should be set before to import the 'settings` module.
# It will raise an error otherwise.
environ["SQLALCHEMY_DATABASE_URL"] = "sqlite://"
environ["LDAP_SERVER"] = "ldap.example.org"
environ["APNS_KEY_ID"] = "UB40ZXKCDZ"
environ[
    "APNS_AUTH_KEY"
] = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtAParbMemenK/+8T
JYWanX1jzKaFcgmupVALPHyaKKKhRANCAARVmMAXI+WPS/vjIsFBHb3B5dQKqgT8
ytZPnlbWNLGGR7tKdB1eLzyBlIVFe9El4Wlvs19ACPRMtE7l75IlbOT+
-----END PRIVATE KEY-----
"""
environ["TEAM_ID"] = "6F44JJ9SDF"
environ["ADMIN_USERS"] = "admin1,admin2"

from app.main import app  # noqa E402
from app.database import engine  # noqa E402
from . import factories  # noqa E402

Session = sessionmaker()
register(factories.UserFactory)
register(factories.ServiceFactory)
register(factories.NotificationFactory)


@pytest.fixture(scope="session")
def connection():
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="function")
def db(connection) -> Generator:
    transaction = connection.begin()
    session = Session(bind=connection)
    factories.UserFactory._meta.sqlalchemy_session = session
    factories.ServiceFactory._meta.sqlalchemy_session = session
    factories.NotificationFactory._meta.sqlalchemy_session = session
    yield session
    session.close()
    transaction.rollback()


@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c
