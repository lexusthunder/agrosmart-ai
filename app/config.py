"""Configurari globale pentru AgroSmart AI.

Foloseste pydantic-settings pentru a citi din .env si environment variables.
Toate pragurile algoritmului de decizie sunt configurabile aici.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Configurari aplicatie."""

    # ---- App
    app_name: str = "AgroSmart AI"
    app_env: str = "development"
    debug: bool = True

    # ---- Database
    database_url: str = f"sqlite:///{DATA_DIR / 'agrosmart.db'}"

    # ---- Securitate
    secret_key: str = Field(
        default="change-me-in-production-please-use-a-long-random-key-min-32-chars",
        min_length=32,
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ---- API
    api_host: str = "0.0.0.0"  # noqa: S104 — bind public for container deploy
    api_port: int = 8000

    # ---- Dashboard
    dashboard_port: int = 7860
    dashboard_api_url: str = "http://localhost:8000"
    # share=True genereaza URL public temporar prin tunelul Gradio (gradio.live, ~72h)
    gradio_share: bool = False

    # ---- CORS
    cors_origins: str = "http://localhost:7860,http://localhost:3000"

    # ---- Praguri decizie (configurabile per cultura)
    threshold_humidity_low: float = 30.0
    threshold_humidity_high: float = 80.0
    threshold_ph_low: float = 5.5
    threshold_ph_high: float = 7.5
    threshold_temp_low: float = 5.0
    threshold_temp_high: float = 35.0

    # ---- SMTP (optional - daca lipseste, alertele merg in data/alerts.log)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@agrosmart.ai"
    smtp_use_tls: bool = True

    # ---- Rate limiting
    rate_limit_default: str = "60/minute"

    # ---- LLM (Claude API) — optional
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 800

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Returneaza lista de origini CORS din string-ul comma-separated."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cache settings instance to avoid re-parsing .env on every call."""
    return Settings()


settings = get_settings()
