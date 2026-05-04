"""Schema Pydantic - DTO-uri pentru request/response API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

# ----------------------------- Auth ----------------------------- #


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["fermier"])
    email: EmailStr = Field(examples=["fermier@agro.ro"])
    full_name: Optional[str] = Field(default=None, examples=["Ion Popescu"])
    password: str = Field(min_length=8, examples=["agrosmart2025"])


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str  # username
    exp: int


# ----------------------------- Sensors ----------------------------- #


class SenzorIn(BaseModel):
    """Date primite de la senzor / dashboard.

    Accepta atat aliasurile scurte ("lat"/"lon") cat si formele complete
    ("latitudine"/"longitudine") pentru compatibilitate cu README-ul.
    """

    model_config = ConfigDict(populate_by_name=True)

    lat: float = Field(
        ge=-90.0,
        le=90.0,
        examples=[46.77],
        validation_alias=AliasChoices("lat", "latitudine"),
        serialization_alias="lat",
    )
    lon: float = Field(
        ge=-180.0,
        le=180.0,
        examples=[23.62],
        validation_alias=AliasChoices("lon", "longitudine"),
        serialization_alias="lon",
    )
    ph: float = Field(ge=0.0, le=14.0, examples=[6.5])
    umiditate: float = Field(ge=0.0, le=100.0, examples=[24.0])
    temperatura: float = Field(ge=-50.0, le=80.0, examples=[28.0])


class DecizieOut(BaseModel):
    """Raspunsul algoritmului de decizie."""

    actiune: str = Field(examples=["PORNESTE IRIGAREA"])
    motiv: str = Field(examples=["Umiditate scazuta: 24.0% (prag 30%)"])
    ph_status: str = Field(examples=["OPTIM"])
    alerta: bool = False


class SenzorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lat: float
    lon: float
    ph: float
    umiditate: float
    temperatura: float
    actiune: str
    motiv: Optional[str] = None
    alerta: bool
    timestamp: datetime


class AnalizaResponse(DecizieOut):
    """Raspunsul complet la /sensors/analiza."""

    id: int
    timestamp: datetime


class AnalyticsSummary(BaseModel):
    total_citiri: int
    citiri_24h: int
    procent_alerte: float
    ph_mediu: Optional[float] = None
    umiditate_medie: Optional[float] = None
    temperatura_medie: Optional[float] = None
    actiuni_frecvente: dict[str, int]


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    valoare: float


class TimeseriesResponse(BaseModel):
    metric: str
    days: int
    points: list[TimeseriesPoint]


# ----------------------------- ML ----------------------------- #


class CropInput(BaseModel):
    """Input pentru recomandarea de cultura (parametri sol + climat)."""

    model_config = ConfigDict(protected_namespaces=())

    N: float = Field(ge=0, le=300, description="Azot (kg/ha)", examples=[90])
    P: float = Field(ge=0, le=300, description="Fosfor (kg/ha)", examples=[42])
    K: float = Field(ge=0, le=300, description="Potasiu (kg/ha)", examples=[43])
    temperature: float = Field(ge=-10, le=60, examples=[20.87])
    humidity: float = Field(ge=0, le=100, examples=[82.0])
    ph: float = Field(ge=0, le=14, examples=[6.5])
    rainfall: float = Field(ge=0, le=1000, description="mm/an", examples=[202.9])
    model_ales: Optional[str] = Field(
        default=None,
        description="Numele modelului (RandomForest|ExtraTrees|GradientBoosting|LogisticRegression). Daca lipseste, foloseste cel mai bun.",
    )


class CropRecommendation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    cultura_recomandata: str
    incredere: float
    top_3: list[tuple[str, float]]
    model_folosit: str = "RandomForest"
    model_disponibil: bool = True


class ChatMessage(BaseModel):
    """Mesaj pentru chat-ul cu LLM."""

    intrebare: str = Field(min_length=1, max_length=2000, examples=["Ce face AgroSmart AI?"])
    istoric: list[dict] = Field(
        default_factory=list,
        description="Istoric mesaje [{role: 'user'|'assistant', content: '...'}]",
    )


class ChatResponse(BaseModel):
    raspuns: str
    model: str = "claude-haiku-4-5"
    tokens_utilizate: Optional[int] = None
    cache_hit: bool = False
