"""Modele SQLModel - schema bazei de date."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Utilizator (fermier) autentificat."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = Field(default=None)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SenzorDate(SQLModel, table=True):
    """O citire de senzor IoT cu decizia generata de algoritm."""

    __tablename__ = "senzori_date"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Locatie
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)

    # Masuratori
    ph: float = Field(ge=0.0, le=14.0)
    umiditate: float = Field(ge=0.0, le=100.0)
    temperatura: float = Field(ge=-50.0, le=80.0)

    # Decizia algoritmului
    actiune: str = Field(default="OK", max_length=64)
    motiv: Optional[str] = Field(default=None, max_length=255)
    alerta: bool = Field(default=False)

    # Metadate
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
