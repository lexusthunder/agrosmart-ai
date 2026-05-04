"""Aplicatia FastAPI principala AgroSmart AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app import __version__
from app.config import settings
from app.database import init_db
from app.observability import REGISTRY, configure_logging
from app.routers import analytics, auth, ml, sensors


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Init DB + logging la startup."""
    configure_logging("DEBUG" if settings.debug else "INFO")
    init_db()
    yield


limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

app = FastAPI(
    title=settings.app_name,
    description=(
        "API pentru sistemul de monitorizare si decizie agricola AgroSmart AI.\n\n"
        "Trimite date de senzor (GPS, pH, umiditate, temperatura) si primesti "
        "decizii automate (irigare, ajustare pH, alerte termice).\n\n"
        "Include un model ML (RandomForest) pentru recomandarea de culturi pe baza "
        "compozitiei solului si a climatului."
    ),
    version=__version__,
    contact={"name": "Ureche Ionel Alexandru"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(sensors.router)
app.include_router(analytics.router)
app.include_router(ml.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
        "metrics": "/metrics",
        "harta": "/sensors/map",
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics", tags=["meta"], include_in_schema=False)
def metrics(_request: Request) -> PlainTextResponse:
    """Prometheus exposition format."""
    return PlainTextResponse(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
