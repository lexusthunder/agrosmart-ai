"""Endpoint-uri pentru date de senzor si analiza in timp real."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlmodel import desc, select

from app.decision import decide
from app.deps import CurrentUser, SessionDep
from app.models import SenzorDate
from app.notifications import send_alert
from app.observability import nr_alerte_total, nr_citiri_total
from app.schemas import AnalizaResponse, SenzorIn, SenzorRead

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/analiza", response_model=AnalizaResponse, status_code=status.HTTP_201_CREATED)
def analiza_date(
    payload: SenzorIn,
    session: SessionDep,
    user: CurrentUser,
    background: BackgroundTasks,
) -> AnalizaResponse:
    """Primeste o citire de senzor, ruleaza algoritmul de decizie si o salveaza."""
    decizie = decide(payload)

    record = SenzorDate(
        lat=payload.lat,
        lon=payload.lon,
        ph=payload.ph,
        umiditate=payload.umiditate,
        temperatura=payload.temperatura,
        actiune=decizie.actiune,
        motiv=decizie.motiv,
        alerta=decizie.alerta,
        user_id=user.id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    nr_citiri_total.inc()
    if decizie.alerta:
        nr_alerte_total.inc()
        background.add_task(
            send_alert,
            destinatar=user.email,
            subiect=f"[AgroSmart] Alerta: {decizie.actiune}",
            mesaj=(
                f"Locatie: ({payload.lat}, {payload.lon})\n"
                f"pH: {payload.ph}  Umid: {payload.umiditate}%  T: {payload.temperatura}°C\n"
                f"Decizie: {decizie.actiune}\n"
                f"Motiv: {decizie.motiv}\n"
            ),
        )

    return AnalizaResponse(
        id=record.id,  # type: ignore[arg-type]
        actiune=decizie.actiune,
        motiv=decizie.motiv,
        ph_status=decizie.ph_status,
        alerta=decizie.alerta,
        timestamp=record.timestamp,
    )


@router.get("/", response_model=list[SenzorRead])
def list_citiri(
    session: SessionDep,
    user: CurrentUser,  # noqa: ARG001
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    doar_alerte: bool = False,
) -> list[SenzorDate]:
    """Listeaza ultimele citiri (paginat)."""
    stmt = select(SenzorDate).order_by(desc(SenzorDate.timestamp)).offset(offset).limit(limit)
    if doar_alerte:
        stmt = stmt.where(SenzorDate.alerta.is_(True))  # type: ignore[union-attr]
    return list(session.exec(stmt).all())


@router.get("/map", response_class=HTMLResponse, include_in_schema=True)
def harta_citiri(
    session: SessionDep,
    user: CurrentUser,  # noqa: ARG001
    limit: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> HTMLResponse:
    """Returneaza harta interactiva Folium cu markere colorate per status."""
    import folium

    stmt = select(SenzorDate).order_by(desc(SenzorDate.timestamp)).limit(limit)
    citiri = list(session.exec(stmt).all())

    if citiri:
        avg_lat = sum(c.lat for c in citiri) / len(citiri)
        avg_lon = sum(c.lon for c in citiri) / len(citiri)
    else:
        avg_lat, avg_lon = 45.9432, 24.9668  # centrul Romaniei

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=7, tiles="OpenStreetMap")

    for c in citiri:
        if c.alerta:
            color = "red"
            icon = "exclamation-sign"
        elif c.actiune.upper().startswith("OK"):
            color = "green"
            icon = "ok-sign"
        else:
            color = "orange"
            icon = "warning-sign"

        popup_html = (
            f"<b>#{c.id}</b><br>"
            f"<b>{c.actiune}</b><br>"
            f"pH: {c.ph} | Um: {c.umiditate}% | T: {c.temperatura}°C<br>"
            f"<small>{c.timestamp:%Y-%m-%d %H:%M}</small><br>"
            f"<i>{c.motiv or ''}</i>"
        )
        folium.Marker(
            location=[c.lat, c.lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon=icon),
            tooltip=f"#{c.id} — {c.actiune}",
        ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                background: white; padding: 10px 14px; border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2); font-family: sans-serif;
                font-size: 13px;">
      <b>Legenda</b><br>
      <span style="color:green">●</span> OK<br>
      <span style="color:orange">●</span> Actiune<br>
      <span style="color:red">●</span> Alerta
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return HTMLResponse(content=m.get_root().render())


@router.get("/{citire_id}", response_model=SenzorRead)
def detalii_citire(
    citire_id: int,
    session: SessionDep,
    user: CurrentUser,  # noqa: ARG001
) -> SenzorDate:
    record = session.get(SenzorDate, citire_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Citire inexistenta")
    return record
