"""Modul ML — incarcare lazy a modelului antrenat + functie de predictie.

Modelul se incarca la prima cerere si se pastreaza in memorie via lru_cache.
Daca artefactul lipseste, predict_crop returneaza None (gracefull degradation).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

MODEL_PATH = DATA_DIR / "agrosmart_model.joblib"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


@dataclass(frozen=True)
class CropPrediction:
    cultura_recomandata: str
    incredere: float
    top_3: list[tuple[str, float]]


@lru_cache(maxsize=1)
def _load_bundle() -> Optional[dict]:
    """Incarca bundle-ul (model + label encoder) o singura data."""
    if not MODEL_PATH.exists():
        logger.warning("Model ML lipseste la %s. Ruleaza scripts/train_model.py.", MODEL_PATH)
        return None
    try:
        import joblib

        bundle = joblib.load(MODEL_PATH)
        logger.info("Model ML incarcat din %s (versiune %s)", MODEL_PATH, bundle.get("version"))
        return bundle
    except Exception as exc:  # pragma: no cover
        logger.exception("Eroare la incarcarea modelului ML: %s", exc)
        return None


def model_available() -> bool:
    return _load_bundle() is not None


def model_metadata() -> dict:
    bundle = _load_bundle()
    if bundle is None:
        return {"loaded": False, "path": str(MODEL_PATH)}
    return {
        "loaded": True,
        "path": str(MODEL_PATH),
        "version": bundle.get("version"),
        "n_classes": len(bundle["label_encoder"].classes_),
        "features": bundle.get("features", FEATURES),
    }


def predict_crop(
    N: float,  # noqa: N803 — convention agronomica
    P: float,  # noqa: N803
    K: float,  # noqa: N803
    temperature: float,
    humidity: float,
    ph: float,
    rainfall: float,
) -> Optional[CropPrediction]:
    """Recomanda cultura optima pe baza parametrilor de sol+climat.

    Returneaza None daca modelul nu e disponibil.
    """
    bundle = _load_bundle()
    if bundle is None:
        return None

    model = bundle["model"]
    le = bundle["label_encoder"]

    x = np.array([[N, P, K, temperature, humidity, ph, rainfall]], dtype=float)
    probs = model.predict_proba(x)[0]

    order = np.argsort(probs)[::-1]
    top_idx = order[:3]
    top_3 = [(le.classes_[i], float(probs[i])) for i in top_idx]

    best_idx = int(order[0])
    return CropPrediction(
        cultura_recomandata=str(le.classes_[best_idx]),
        incredere=float(probs[best_idx]),
        top_3=top_3,
    )


def reset_cache() -> None:
    """Util pentru teste — forteaza reincarcarea modelului."""
    _load_bundle.cache_clear()
