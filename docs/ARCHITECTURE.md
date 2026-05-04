# Arhitectură — AgroSmart AI

> **TL;DR:** API FastAPI + dashboard Gradio + ML RandomForest, totul rulând pe Python 3.10+ cu SQLite local (sau Postgres în prod). Stateless, container-ready, observability prin Prometheus + JSON logs.

## 1. Diagramă de ansamblu

```mermaid
flowchart LR
    subgraph CLIENT
      D[Dashboard Gradio<br/>:7860]
      F[Senzor IoT<br/>simulator]
      M[Mobile / cURL]
    end

    subgraph API[FastAPI :8000]
      AUTH[/auth/login,register,me/]
      SEN[/sensors/analiza,map/]
      ANA[/analytics/summary,timeseries/]
      ML[/ml/predict-crop/]
      MET[/metrics + /health/]
    end

    subgraph CORE[Domeniu]
      DEC[decision.py<br/>reguli irigare/pH/temp]
      MOD[ml.py<br/>RandomForest 99.3% acc]
      NOT[notifications.py<br/>SMTP + alerts.log]
      OBS[observability.py<br/>Prometheus + JSON log]
    end

    subgraph STORE
      DB[(SQLite<br/>users, senzori_date)]
      MDL[(joblib bundle<br/>data/agrosmart_model.joblib)]
      CSV[(Crop_recommendation.csv<br/>2200 randuri x 22 culturi)]
    end

    D --> AUTH
    D --> SEN
    D --> ANA
    D --> ML
    F --> SEN
    M --> API

    SEN --> DEC
    SEN --> NOT
    SEN --> OBS
    SEN --> DB

    ML --> MOD
    MOD --> MDL

    ANA --> DB
    AUTH --> DB

    CSV -.train.-> MDL
```

## 2. Fluxul "citire senzor → decizie → alertă"

```mermaid
sequenceDiagram
    participant Senzor
    participant API as FastAPI /sensors/analiza
    participant Decision as decision.py
    participant DB
    participant Notify as notifications.send_alert
    participant SMTP

    Senzor->>API: POST {lat, lon, ph, umiditate, temperatura} + JWT
    API->>Decision: decide(payload)
    Decision-->>API: {actiune, motiv, ph_status, alerta}
    API->>DB: INSERT senzori_date
    alt alerta == True
      API->>Notify: BackgroundTask
      Notify->>SMTP: send (sau alerts.log dacă SMTP lipsește)
    end
    API-->>Senzor: 201 {id, actiune, motiv, alerta, timestamp}
```

## 3. Componente

| Modul | Rol | Test |
|---|---|---|
| `app/main.py` | FastAPI app, middleware, lifespan, /metrics | smoke prin `test_*.py` |
| `app/config.py` | Settings via pydantic-settings, env-driven | — |
| `app/database.py` | SQLModel session + init_db | conftest in-memory |
| `app/security.py` | bcrypt + JWT (HS256) | `test_auth.py` |
| `app/decision.py` | Reguli agro deterministe | `test_decision.py` (10 cazuri) |
| `app/ml.py` | Lazy load + predict_crop | `test_ml.py` (5 teste, mock) |
| `app/notifications.py` | SMTP + fallback log | — (integration-only) |
| `app/observability.py` | Prometheus counters + JSON logging | — |
| `app/routers/*.py` | Auth, sensors, analytics, ml | toate testate |
| `dashboard/app.py` | Gradio UI cu tab-uri | manual |
| `scripts/train_model.py` | Antrenare RandomForest 300 trees | smoke prin CI |

## 4. Decizii de design

- **SQLite default + DATABASE_URL override** — zero setup local, 1-line switch la Postgres.
- **JWT stateless** — fără sesiuni server-side; tokenul are doar `sub` + `exp`.
- **Lazy ML loading prin `lru_cache`** — primul request încarcă, restul sunt instant.
- **Background tasks pentru SMTP** — răspunsul API nu așteaptă rețeaua.
- **Folium server-side render** — hartă HTML embeddable în iframe, fără dependență JS.
- **Rate limit `slowapi`** — 60/min default, configurabil prin `RATE_LIMIT_DEFAULT`.

## 5. Hărți pentru extensii

- **Multi-tenancy**: adaugă `org_id` în `User` + index parțial pe `senzori_date`.
- **Predicții serie-temporală**: înlocuiește RF cu Prophet/LSTM, expune `/ml/predict-yield`.
- **Edge inference**: portează `app/ml.py` într-un container ARM (Raspberry Pi).
