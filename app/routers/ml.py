"""Endpoint-uri ML — recomandare cultura + chat LLM."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser
from app.llm import chat as llm_chat
from app.ml import list_models, model_metadata, predict_crop
from app.observability import nr_ml_predict
from app.schemas import ChatMessage, ChatResponse, CropInput, CropRecommendation

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/info")
def info(user: CurrentUser) -> dict:  # noqa: ARG001
    """Returneaza metadate despre toate modelele ML incarcate."""
    return model_metadata()


@router.get("/models")
def models(user: CurrentUser) -> dict:  # noqa: ARG001
    """Listeaza modelele disponibile + metricele lor."""
    meta = model_metadata()
    return {
        "available": meta.get("available_models", []),
        "best": meta.get("best_model"),
        "metrics": meta.get("metrics", {}),
    }


@router.post("/predict-crop", response_model=CropRecommendation)
def predict_crop_endpoint(
    payload: CropInput,
    user: CurrentUser,  # noqa: ARG001
) -> CropRecommendation:
    """Recomanda cultura optima pe baza solului si climatului. Acepta `model_ales` pentru a alege modelul."""
    pred = predict_crop(
        N=payload.N,
        P=payload.P,
        K=payload.K,
        temperature=payload.temperature,
        humidity=payload.humidity,
        ph=payload.ph,
        rainfall=payload.rainfall,
        model=payload.model_ales,
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
        model_folosit=pred.model_folosit,
        model_disponibil=True,
    )


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatMessage,
    user: CurrentUser,  # noqa: ARG001
) -> ChatResponse:
    """Chat cu un asistent LLM (Claude) care cunoaste sistemul AgroSmart AI."""
    return llm_chat(payload)


# Suprima warning despre ml.list_models neutilizat
_ = list_models
