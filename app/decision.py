"""Algoritmul de decizie - logica sistemului AgroSmart AI.

Transforma o citire de senzor in actiune agricola concreta, folosind praguri
configurabile per cultura/sezon (vezi `app.config.settings`).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, settings
from app.schemas import DecizieOut, SenzorIn


@dataclass(frozen=True)
class Praguri:
    """Pragurile algoritmului - pot fi inlocuite per cultura."""

    humidity_low: float
    humidity_high: float
    ph_low: float
    ph_high: float
    temp_low: float
    temp_high: float

    @classmethod
    def from_settings(cls, s: Settings = settings) -> Praguri:
        return cls(
            humidity_low=s.threshold_humidity_low,
            humidity_high=s.threshold_humidity_high,
            ph_low=s.threshold_ph_low,
            ph_high=s.threshold_ph_high,
            temp_low=s.threshold_temp_low,
            temp_high=s.threshold_temp_high,
        )


# Constante actiuni - evita typo-urile
ACTIUNE_PORNESTE_IRIGARE = "PORNESTE IRIGAREA"
ACTIUNE_OPRESTE_IRIGARE = "OPRESTE IRIGAREA"
ACTIUNE_ADAUGA_CALCAR = "ADAUGA CALCAR"
ACTIUNE_ADAUGA_SULF = "ADAUGA SULF"
ACTIUNE_ACTIVEAZA_RACIRE = "ACTIVEAZA RACIRE"
ACTIUNE_ALERTA_INGHET = "ALERTA INGHET"
ACTIUNE_OK = "OK"


def _ph_status(ph: float, p: Praguri) -> str:
    if ph < p.ph_low:
        return "ACID"
    if ph > p.ph_high:
        return "ALCALIN"
    return "OPTIM"


def decide(date: SenzorIn, praguri: Praguri | None = None) -> DecizieOut:
    """Genereaza o decizie pe baza datelor de senzor.

    Prioritatea actiunilor (de sus in jos):
      1. Alerta inghet (temp foarte mica)  -> alerta=True
      2. Activeaza racire  (temp foarte mare) -> alerta=True
      3. Porneste irigarea  (umiditate scazuta)
      4. Opreste irigarea  (umiditate ridicata)
      5. Adauga calcar  (pH acid)
      6. Adauga sulf  (pH alcalin)
      7. OK
    """
    p = praguri or Praguri.from_settings()
    ph_st = _ph_status(date.ph, p)

    # 1-2 alerte termice (prioritate maxima)
    if date.temperatura < p.temp_low:
        return DecizieOut(
            actiune=ACTIUNE_ALERTA_INGHET,
            motiv=f"Temperatura {date.temperatura:.1f}°C sub pragul de {p.temp_low}°C",
            ph_status=ph_st,
            alerta=True,
        )
    if date.temperatura > p.temp_high:
        return DecizieOut(
            actiune=ACTIUNE_ACTIVEAZA_RACIRE,
            motiv=f"Temperatura {date.temperatura:.1f}°C peste pragul de {p.temp_high}°C",
            ph_status=ph_st,
            alerta=True,
        )

    # 3-4 irigare
    if date.umiditate < p.humidity_low:
        return DecizieOut(
            actiune=ACTIUNE_PORNESTE_IRIGARE,
            motiv=f"Umiditate scazuta: {date.umiditate:.1f}% (prag {p.humidity_low}%)",
            ph_status=ph_st,
            alerta=False,
        )
    if date.umiditate > p.humidity_high:
        return DecizieOut(
            actiune=ACTIUNE_OPRESTE_IRIGARE,
            motiv=f"Umiditate ridicata: {date.umiditate:.1f}% (prag {p.humidity_high}%)",
            ph_status=ph_st,
            alerta=False,
        )

    # 5-6 corectie pH
    if date.ph < p.ph_low:
        return DecizieOut(
            actiune=ACTIUNE_ADAUGA_CALCAR,
            motiv=f"pH acid: {date.ph:.2f} (prag {p.ph_low})",
            ph_status=ph_st,
            alerta=False,
        )
    if date.ph > p.ph_high:
        return DecizieOut(
            actiune=ACTIUNE_ADAUGA_SULF,
            motiv=f"pH alcalin: {date.ph:.2f} (prag {p.ph_high})",
            ph_status=ph_st,
            alerta=False,
        )

    # 7 totul OK
    return DecizieOut(
        actiune=ACTIUNE_OK,
        motiv="Toti parametrii sunt in limite normale",
        ph_status=ph_st,
        alerta=False,
    )
