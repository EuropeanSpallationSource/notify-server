from fastapi.testclient import TestClient
from app import models, utils


def test_login_invalid_credentials(client: TestClient, mocker):
    mock_authenticate_user = mocker.patch(
        "app.api.login.ldap.authenticate_user", return_value=False
    )
    username = "johndoe"
    password = "secret"
    response = client.post(
        "/api/v1/login", data={"username": username, "password": password}
    )
    mock_authenticate_user.assert_called_once_with(username, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}


def test_login_new_user(client: TestClient, db, mocker):
    mock_authenticate_user = mocker.patch(
        "app.api.login.ldap.authenticate_user", return_value=True
    )
    username = "johndoe"
    password = "secret"
    assert (
        db.query(models.User).filter(models.User.username == username).first() is None
    )
    response = client.post(
        "/api/v1/login", data={"username": username, "password": password}
    )
    mock_authenticate_user.assert_called_once_with(username, password)
    assert response.status_code == 201
    db_user = db.query(models.User).filter(models.User.username == username).first()
    assert db_user.username == username
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    assert utils.decode_access_token(token)["sub"] == username


def test_login_existing_user(client: TestClient, db, mocker, user):
    mock_authenticate_user = mocker.patch(
        "app.api.login.ldap.authenticate_user", return_value=True
    )
    password = "secret"
    assert (
        db.query(models.User).filter(models.User.username == user.username).first()
        == user
    )
    response = client.post(
        "/api/v1/login", data={"username": user.username, "password": password}
    )
    mock_authenticate_user.assert_called_once_with(user.username, password)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    assert utils.decode_access_token(token)["sub"] == user.username
