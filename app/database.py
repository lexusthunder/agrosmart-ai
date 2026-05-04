"""Setup engine si sesiuni SQLModel."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# `connect_args` necesar doar pentru SQLite (single-thread fiscal)
connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def init_db() -> None:
    """Creeaza toate tabelele definite in models.py."""
    # Importurile se fac aici ca SQLModel.metadata sa stie despre toate tabelele
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency FastAPI pentru sesiuni DB."""
    with Session(engine) as session:
        yield session
