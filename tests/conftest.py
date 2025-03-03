import datetime
import secrets
import pytest
from fastapi.testclient import TestClient
from starlette.config import environ
from sqlalchemy.orm import sessionmaker
from pytest_factoryboy import register
from typing import Generator

# Overwrite default settings.
# Note that those should be set before to import the 'settings' module.
# It will raise an error otherwise.
environ["SQLALCHEMY_DATABASE_URL"] = "sqlite://"
environ["LDAP_SERVER"] = "ldap.example.org"
environ["APNS_KEY_ID"] = "UB40ZXKCDZ"
environ["AUTHENTICATION_URL"] = "https://auth.example.org/login"
environ["APNS_AUTH_KEY"] = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtAParbMemenK/+8T
JYWanX1jzKaFcgmupVALPHyaKKKhRANCAARVmMAXI+WPS/vjIsFBHb3B5dQKqgT8
ytZPnlbWNLGGR7tKdB1eLzyBlIVFe9El4Wlvs19ACPRMtE7l75IlbOT+
-----END PRIVATE KEY-----
"""
environ["TEAM_ID"] = "6F44JJ9SDF"
environ["ADMIN_USERS"] = "admin1,admin2"
environ["NB_PARALLEL_PUSH"] = "2"
environ["FIREBASE_PROJECT_ID"] = "my-project"
environ["GOOGLE_APPLICATION_CREDENTIALS"] = "test-key.json"

from app.main import original_api, app  # noqa E402
from app.database import Base, engine  # noqa E402
from app import deps  # noqa E402
from app.utils import create_access_token  # noqa E402
from . import factories  # noqa E402

Session = sessionmaker()
register(factories.UserFactory)
register(factories.ServiceFactory)
register(factories.NotificationFactory)


@pytest.fixture(scope="session")
def connection():
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(autouse=True, scope="function")
def db(connection) -> Generator:
    transaction = connection.begin()
    session = Session(bind=connection)
    factories.UserFactory._meta.sqlalchemy_session = session
    factories.ServiceFactory._meta.sqlalchemy_session = session
    factories.NotificationFactory._meta.sqlalchemy_session = session
    original_api.dependency_overrides[deps.get_db] = lambda: session
    yield session
    session.close()
    transaction.rollback()


@pytest.fixture
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_token_headers(user):
    token = create_access_token(
        user.username,
        expire=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token_headers(user_factory):
    admin = user_factory(is_admin=True)
    token = create_access_token(
        admin.username,
        expire=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(params=["v1", "v2"])
def api_version(request):
    return request.param


@pytest.fixture
def make_device_token():
    def _make_device_token(length):
        return secrets.token_hex(int(length / 2))

    return _make_device_token


@pytest.fixture
def notification_date():
    def _notification_date(days_old):
        return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=days_old
        )

    return _notification_date
