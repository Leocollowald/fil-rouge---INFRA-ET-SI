import pytest
from fastapi.testclient import TestClient


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

USER_DATA = {
    "email": "test@yplaza.fr",
    "password": "motdepasse123",
    "first_name": "Jean",
    "last_name": "Dupont",
}


def test_register_success(client: TestClient):
    response = client.post(REGISTER_URL, json=USER_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == USER_DATA["email"]
    assert data["role"] == "client"
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient):
    client.post(REGISTER_URL, json=USER_DATA)
    response = client.post(REGISTER_URL, json=USER_DATA)
    assert response.status_code == 409


def test_register_weak_password(client: TestClient):
    payload = {**USER_DATA, "email": "other@yplaza.fr", "password": "short"}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


def test_login_success(client: TestClient):
    client.post(REGISTER_URL, json=USER_DATA)
    response = client.post(LOGIN_URL, json={"email": USER_DATA["email"], "password": USER_DATA["password"]})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    client.post(REGISTER_URL, json=USER_DATA)
    response = client.post(LOGIN_URL, json={"email": USER_DATA["email"], "password": "mauvais"})
    assert response.status_code == 401


def test_login_unknown_email(client: TestClient):
    response = client.post(LOGIN_URL, json={"email": "inconnu@yplaza.fr", "password": "test1234"})
    assert response.status_code == 401
