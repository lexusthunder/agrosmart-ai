"""Teste pentru endpoint-urile de autentificare."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    r = client.post(
        "/auth/register",
        json={
            "username": "nou",
            "email": "nou@agrosmart.ro",
            "full_name": "Userul Nou",
            "password": "parolasecreta",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "nou"
    assert "hashed_password" not in body  # niciodata in raspuns


def test_register_duplicat(client: TestClient, demo_user):  # noqa: ARG001
    r = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "altul@agrosmart.ro",
            "password": "parolasecreta",
        },
    )
    assert r.status_code == 409


def test_login_success(client: TestClient, demo_user):  # noqa: ARG001
    r = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass1234"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_parola_gresita(client: TestClient, demo_user):  # noqa: ARG001
    r = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "gresit"},
    )
    assert r.status_code == 401


def test_me_necesita_token(client: TestClient):
    assert client.get("/auth/me").status_code == 401


def test_me_returneaza_userul(client: TestClient, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"
