"""Teste pentru endpoint-ul /ml/predict-crop si modulul app.ml."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient


class _FakeLE:
    classes_ = np.array(["rice", "wheat", "corn"])


class _FakeModel:
    def predict_proba(self, x):  # noqa: ARG002
        return np.array([[0.7, 0.2, 0.1]])


def _fake_bundle() -> dict:
    return {
        "model": _FakeModel(),
        "label_encoder": _FakeLE(),
        "features": ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"],
        "version": "test-1.0",
    }


def test_predict_crop_returneaza_top3_corect(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "N": 90,
        "P": 42,
        "K": 43,
        "temperature": 21.0,
        "humidity": 82.0,
        "ph": 6.5,
        "rainfall": 200.0,
    }
    with patch("app.ml._load_bundle", return_value=_fake_bundle()):
        r = client.post("/ml/predict-crop", json=payload, headers=auth_headers)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cultura_recomandata"] == "rice"
    assert abs(body["incredere"] - 0.7) < 1e-6
    assert len(body["top_3"]) == 3
    assert body["top_3"][0] == ["rice", 0.7]
    assert body["model_disponibil"] is True


def test_predict_crop_503_cand_modelul_lipseste(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "N": 90,
        "P": 42,
        "K": 43,
        "temperature": 21.0,
        "humidity": 82.0,
        "ph": 6.5,
        "rainfall": 200.0,
    }
    with patch("app.ml._load_bundle", return_value=None):
        r = client.post("/ml/predict-crop", json=payload, headers=auth_headers)

    assert r.status_code == 503
    assert "train_model" in r.json()["detail"]


def test_predict_crop_necesita_auth(client: TestClient) -> None:
    r = client.post(
        "/ml/predict-crop",
        json={"N": 1, "P": 1, "K": 1, "temperature": 20, "humidity": 50, "ph": 6, "rainfall": 100},
    )
    assert r.status_code == 401


def test_predict_crop_valideaza_inputul(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    bad = {"N": -5, "P": 1, "K": 1, "temperature": 20, "humidity": 50, "ph": 6, "rainfall": 100}
    r = client.post("/ml/predict-crop", json=bad, headers=auth_headers)
    assert r.status_code == 422


def test_ml_info_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("app.ml._load_bundle", return_value=_fake_bundle()):
        r = client.get("/ml/info", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["loaded"] is True
    assert body["n_classes"] == 3
