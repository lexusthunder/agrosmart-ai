"""Modul ML — incarcare lazy a bundle-ului multi-model + functie de predictie.

Bundle-ul (data/agrosmart_model.joblib) contine 4 modele antrenate:
RandomForest, GradientBoosting, ExtraTrees, LogisticRegression.
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
    model_folosit: str


@lru_cache(maxsize=1)
def _load_bundle() -> Optional[dict]:
    """Incarca bundle-ul (multi-model) o singura data."""
    if not MODEL_PATH.exists():
        logger.warning("Model ML lipseste la %s. Ruleaza scripts/train_model.py.", MODEL_PATH)
        return None
    try:
        import joblib

        bundle = joblib.load(MODEL_PATH)
        # Compat pe vechiul format single-model
        if "model" in bundle and "models" not in bundle:
            bundle["models"] = {"RandomForest": bundle["model"]}
            bundle["best_model"] = "RandomForest"
        logger.info("Bundle ML incarcat (versiune %s, %d modele)",
                    bundle.get("version"), len(bundle.get("models", {})))
        return bundle
    except Exception as exc:  # pragma: no cover
        logger.exception("Eroare la incarcarea modelului ML: %s", exc)
        return None


def model_available() -> bool:
    return _load_bundle() is not None


def list_models() -> list[str]:
    bundle = _load_bundle()
    if bundle is None:
        return []
    return list(bundle.get("models", {}).keys())


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
        "available_models": list_models(),
        "best_model": bundle.get("best_model"),
        "metrics": bundle.get("metrics", {}),
    }


def predict_crop(
    N: float,  # noqa: N803
    P: float,  # noqa: N803
    K: float,  # noqa: N803
    temperature: float,
    humidity: float,
    ph: float,
    rainfall: float,
    model: Optional[str] = None,
) -> Optional[CropPrediction]:
    """Recomanda cultura. Daca model e None, foloseste best_model.

    Returneaza None daca bundle-ul nu e disponibil.
    """
    bundle = _load_bundle()
    if bundle is None:
        return None

    models = bundle["models"]
    le = bundle["label_encoder"]

    chosen = model or bundle.get("best_model") or next(iter(models.keys()))
    if chosen not in models:
        logger.warning("Model '%s' nu exista; folosesc '%s'", chosen, bundle.get("best_model"))
        chosen = bundle.get("best_model") or next(iter(models.keys()))
    estimator = models[chosen]

    x = np.array([[N, P, K, temperature, humidity, ph, rainfall]], dtype=float)

    # Toate modelele au predict_proba dupa configurarea noastra
    probs = estimator.predict_proba(x)[0]
    order = np.argsort(probs)[::-1]
    top_3 = [(le.classes_[i], float(probs[i])) for i in order[:3]]
    best_idx = int(order[0])

    return CropPrediction(
        cultura_recomandata=str(le.classes_[best_idx]),
        incredere=float(probs[best_idx]),
        top_3=top_3,
        model_folosit=chosen,
    )


def reset_cache() -> None:
    """Forteaza reincarcarea modelului (util pentru teste)."""
    _load_bundle.cache_clear()
