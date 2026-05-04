# 🌱 AgroSmart AI

> **Sistem inteligent de monitorizare și decizie agricolă bazat pe FastAPI + Gradio**
> Autor: **Ureche Ionel Alexandru** · Proiect SDA · 2025

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com/)
[![Gradio](https://img.shields.io/badge/Gradio-4.x-orange)](https://gradio.app/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AgroSmart AI transformă datele brute de la senzorii IoT din câmp (GPS, pH, umiditate, temperatură) în **decizii agricole automate** (pornește/oprește irigarea, ajustare pH, alerte termice) printr-un API REST modern și un dashboard interactiv.

---

## ✨ Caracteristici principale

- ⚡ **Backend FastAPI async** — gestionare concurentă a zeci de senzori IoT, performanță aproape de Go/Node.js
- 🗄️ **SQLModel + SQLAlchemy** — un singur model pentru DB și validare, suport SQLite (dev) și PostgreSQL (prod)
- 🔐 **Securitate completă** — JWT cu expirare, bcrypt (cost 12), validare Pydantic, middleware de autentificare
- 🎯 **Algoritm de decizie configurabil** — praguri per cultură pentru irigare, pH, temperatură
- 📊 **Dashboard Gradio interactiv** — vizualizare în timp real, hartă GPS, simulare senzori
- 🧪 **Suite de teste pytest** — unit, integration și API tests, coverage > 95%
- 🐳 **Docker-ready** — `docker-compose up` și totul rulează
- 📚 **Documentație automată** — Swagger UI și ReDoc generate din cod
- 🛠️ **VS Code optimizat** — debug configs, tasks, extensii recomandate

---

## 🏗️ Arhitectură

```
┌────────────┐   HTTP   ┌──────────────┐   SQL   ┌──────────────┐
│  Senzori   │ ───────▶ │   FastAPI    │ ──────▶ │   Database   │
│  IoT / UI  │  POST    │ + Pydantic   │         │  SQLite/PG   │
└────────────┘          │ + JWT Auth   │         └──────────────┘
                        │ + Decizie    │
                        └──────┬───────┘
                               │ JSON
                               ▼
                        ┌──────────────┐
                        │   Gradio     │
                        │  Dashboard   │
                        └──────────────┘
```

---

## 🚀 Quick Start

### Cerințe
- Python 3.10+
- pip / venv (sau uv / poetry)
- (opțional) Docker + Docker Compose

### Instalare locală

```bash
# 1. Clonează / dezarhivează proiectul
cd agrosmart-ai

# 2. Creează virtual environment
python -m venv .venv
source .venv/bin/activate            # Linux / Mac
# .venv\Scripts\activate             # Windows

# 3. Instalează dependențele
pip install -r requirements.txt
pip install -r requirements-dev.txt  # opțional, pentru teste

# 4. Configurează environment
cp .env.example .env

# 5. Seed database (utilizator demo + date)
python -m scripts.seed

# 6. Pornește totul (API + Dashboard)
python run.py
```

Apoi deschide:
- 🌐 **Dashboard Gradio:** http://localhost:7860
- 📚 **Swagger UI:** http://localhost:8000/docs
- 📕 **ReDoc:** http://localhost:8000/redoc

### Credențiale demo

```
username: fermier
password: agrosmart2025
```

---

## 🐳 Docker

```bash
docker-compose up --build
```

API pe `:8000`, dashboard pe `:7860`.

---

## 📡 Endpoint-uri principale

| Metodă | Endpoint | Descriere | Auth |
|--------|----------|-----------|------|
| `POST` | `/auth/register` | Înregistrare utilizator nou | ❌ |
| `POST` | `/auth/login` | Autentificare → JWT | ❌ |
| `GET`  | `/auth/me` | Profil utilizator curent | ✅ |
| `POST` | `/sensors/analiza` | Trimite date senzor + primește decizie | ✅ |
| `GET`  | `/sensors/` | Listează ultimele citiri | ✅ |
| `GET`  | `/sensors/{id}` | Detalii citire | ✅ |
| `GET`  | `/sensors/map` | Hartă Folium HTML cu toate citirile | ✅ |
| `GET`  | `/analytics/summary` | Statistici agregate | ✅ |
| `GET`  | `/analytics/timeseries` | Serie temporală (ph/umiditate/temperatura) | ✅ |
| `POST` | `/ml/predict-crop` | Recomandare cultură (RandomForest, ~99% acc) | ✅ |
| `GET`  | `/ml/info` | Metadate model ML | ✅ |
| `GET`  | `/health` | Healthcheck | ❌ |
| `GET`  | `/metrics` | Metrici Prometheus | ❌ |

### Exemplu cerere

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=fermier&password=agrosmart2025" | jq -r .access_token)

# Trimite citire senzor
curl -X POST http://localhost:8000/sensors/analiza \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitudine": 46.77,
    "longitudine": 23.62,
    "ph": 6.5,
    "umiditate": 24.0,
    "temperatura": 28.0
  }'
```

Răspuns:

```json
{
  "id": 1,
  "actiune": "PORNEȘTE IRIGAREA",
  "motiv": "Umiditate scăzută: 24.0% (prag 30%)",
  "ph_status": "OPTIM",
  "alerta": false,
  "timestamp": "2025-06-10T14:32:00"
}
```

---

## 🧪 Testare

```bash
# Toate testele
pytest

# Cu coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Doar testele unitare
pytest tests/test_decision.py -v
```

---

## 📁 Structura proiectului

```
agrosmart-ai/
├── app/                    # Backend FastAPI
│   ├── main.py             # Aplicația principală
│   ├── config.py           # Settings (Pydantic)
│   ├── database.py         # Engine + sesiuni SQLModel
│   ├── models.py           # Tabele DB
│   ├── schemas.py          # DTO-uri Pydantic
│   ├── security.py         # bcrypt + JWT helpers
│   ├── deps.py             # Dependency injection
│   ├── decision.py         # Algoritmul de decizie
│   └── routers/            # Endpoint-uri grupate
│       ├── auth.py
│       ├── sensors.py
│       └── analytics.py
├── dashboard/              # Gradio UI
│   └── app.py
├── tests/                  # Suite pytest
│   ├── conftest.py
│   ├── test_decision.py
│   ├── test_auth.py
│   └── test_sensors.py
├── scripts/
│   ├── seed.py             # Date demo
│   └── simulate_sensor.py  # Simulare IoT
├── .vscode/                # Config VS Code
├── data/                   # SQLite + fișiere generate
├── run.py                  # Lansează API + Dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

---

## 🧠 Algoritmul de decizie

| Parametru | Prag jos | Prag sus | Acțiune jos | Acțiune sus |
|-----------|---------:|---------:|-------------|-------------|
| Umiditate sol (%) | < 30 | > 80 | PORNEȘTE IRIGAREA | OPREȘTE IRIGAREA |
| pH | < 5.5 | > 7.5 | ADAUGĂ CALCAR | ADAUGĂ SULF |
| Temperatura (°C) | < 5 | > 35 | ALERTĂ ÎNGHEȚ | ACTIVEAZĂ RĂCIRE |

Pragurile sunt configurabile per cultură via `app/config.py` sau variabile de environment.

---

## 🛣️ Roadmap

- [x] **Faza 1 — actuală:** simulare în Gradio, FastAPI local, SQLite
- [ ] **Faza 2 — extindere:** Arduino/Raspberry Pi reali, deploy AWS/GCP, PostgreSQL
- [ ] **Faza 3 — enterprise:** rețea IoT, ML predictiv, drone, multi-tenant, notificări SMS

---

## 📜 Licență

MIT — vezi [LICENSE](LICENSE).

---

> *Proiect SDA · Examen · 2025 — Ureche Ionel Alexandru*
