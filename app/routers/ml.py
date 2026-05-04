"""Endpoint-uri ML — recomandare cultura."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser
from app.ml import model_metadata, predict_crop
from app.observability import nr_ml_predict
from app.schemas import CropInput, CropRecommendation

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/info")
def info(user: CurrentUser) -> dict:  # noqa: ARG001
    """Returneaza metadate despre modelul ML incarcat."""
    return model_metadata()


@router.post("/predict-crop", response_model=CropRecommendation)
def predict_crop_endpoint(
    payload: CropInput,
    user: CurrentUser,  # noqa: ARG001
) -> CropRecommendation:
    """Recomanda cultura optima pe baza solului si climatului."""
    pred = predict_crop(
        N=payload.N,
        P=payload.P,
        K=payload.K,
        temperature=payload.temperature,
        humidity=payload.humidity,
        ph=payload.ph,
        rainfall=payload.rainfall,
    )
    if pred is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Modelul ML nu este disponibil. Ruleaza: python -m scripts.train_model"
            ),
        )
    nr_ml_predict.inc()
    return CropRecommendation(
        cultura_recomandata=pred.cultura_recomandata,
        incredere=pred.incredere,
        top_3=pred.top_3,
        model_disponibil=True,
    )
