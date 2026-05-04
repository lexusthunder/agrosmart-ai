"""Endpoint-uri analitice / agregari."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlmodel import func, select

from app.deps import CurrentUser, SessionDep
from app.models import SenzorDate
from app.schemas import AnalyticsSummary, TimeseriesPoint, TimeseriesResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])

_METRIC_COLUMN = {
    "ph": SenzorDate.ph,
    "umiditate": SenzorDate.umiditate,
    "temperatura": SenzorDate.temperatura,
}


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    session: SessionDep,
    user: CurrentUser,  # noqa: ARG001
) -> AnalyticsSummary:
    """Statistici agregate peste toate citirile."""
    total = session.exec(select(func.count()).select_from(SenzorDate)).one()
    if total == 0:
        return AnalyticsSummary(
            total_citiri=0,
            citiri_24h=0,
            procent_alerte=0.0,
            ph_mediu=None,
            umiditate_medie=None,
            temperatura_medie=None,
            actiuni_frecvente={},
        )

    de_la_24h = datetime.utcnow() - timedelta(hours=24)
    citiri_24h = session.exec(
        select(func.count()).select_from(SenzorDate).where(SenzorDate.timestamp >= de_la_24h)
    ).one()

    alerte = session.exec(
        select(func.count()).select_from(SenzorDate).where(SenzorDate.alerta.is_(True))  # type: ignore[union-attr]
    ).one()

    ph_avg = session.exec(select(func.avg(SenzorDate.ph))).one()
    um_avg = session.exec(select(func.avg(SenzorDate.umiditate))).one()
    temp_avg = session.exec(select(func.avg(SenzorDate.temperatura))).one()

    actiuni = session.exec(select(SenzorDate.actiune)).all()
    counter = Counter(actiuni)

    return AnalyticsSummary(
        total_citiri=int(total),
        citiri_24h=int(citiri_24h),
        procent_alerte=round(100.0 * alerte / total, 2) if total else 0.0,
        ph_mediu=round(ph_avg, 2) if ph_avg is not None else None,
        umiditate_medie=round(um_avg, 2) if um_avg is not None else None,
        temperatura_medie=round(temp_avg, 2) if temp_avg is not None else None,
        actiuni_frecvente=dict(counter.most_common(10)),
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
def timeseries(
    session: SessionDep,
    user: CurrentUser,  # noqa: ARG001
    metric: Literal["ph", "umiditate", "temperatura"] = "umiditate",
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> TimeseriesResponse:
    """Returneaza seria temporala pentru o metrica (ultimele N zile)."""
    column = _METRIC_COLUMN[metric]
    de_la = datetime.utcnow() - timedelta(days=days)

    rows = session.exec(
        select(SenzorDate.timestamp, column)
        .where(SenzorDate.timestamp >= de_la)
        .order_by(SenzorDate.timestamp)
    ).all()

    points = [TimeseriesPoint(timestamp=ts, valoare=float(val)) for ts, val in rows]
    return TimeseriesResponse(metric=metric, days=days, points=points)
