"""Teste pentru endpoint-urile de senzori."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "version" in r.json()


def test_analiza_necesita_auth(client: TestClient):
    r = client.post(
        "/sensors/analiza",
        json={
            "lat": 46.77,
            "lon": 23.62,
            "ph": 6.5,
            "umiditate": 24.0,
            "temperatura": 28.0,
        },
    )
    assert r.status_code == 401


def test_analiza_irigare(client: TestClient, auth_headers):
    r = client.post(
        "/sensors/analiza",
        headers=auth_headers,
        json={
            "lat": 46.77,
            "lon": 23.62,
            "ph": 6.5,
            "umiditate": 20.0,  # < 30 -> irigare
            "temperatura": 22.0,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["actiune"] == "PORNESTE IRIGAREA"
    assert body["ph_status"] == "OPTIM"
    assert body["alerta"] is False
    assert "id" in body


def test_listare_si_paginare(client: TestClient, auth_headers):
    # Trimite 3 citiri
    for um in (20, 50, 85):
        client.post(
            "/sensors/analiza",
            headers=auth_headers,
            json={
                "lat": 46.77,
                "lon": 23.62,
                "ph": 6.5,
                "umiditate": um,
                "temperatura": 22.0,
            },
        )

    r = client.get("/sensors/", headers=auth_headers, params={"limit": 10})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3


def test_validare_ph_out_of_range(client: TestClient, auth_headers):
    r = client.post(
        "/sensors/analiza",
        headers=auth_headers,
        json={
            "lat": 46.77,
            "lon": 23.62,
            "ph": 99,  # invalid
            "umiditate": 50,
            "temperatura": 22,
        },
    )
    assert r.status_code == 422


def test_analytics_summary(client: TestClient, auth_headers):
    # Trimite cateva citiri
    for _ in range(3):
        client.post(
            "/sensors/analiza",
            headers=auth_headers,
            json={
                "lat": 46.77,
                "lon": 23.62,
                "ph": 6.5,
                "umiditate": 20,
                "temperatura": 22,
            },
        )
    r = client.get("/analytics/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_citiri"] == 3
    assert "PORNESTE IRIGAREA" in body["actiuni_frecvente"]
