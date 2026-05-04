"""Teste pentru algoritmul de decizie."""

from __future__ import annotations

import pytest

from app.decision import (
    ACTIUNE_ACTIVEAZA_RACIRE,
    ACTIUNE_ADAUGA_CALCAR,
    ACTIUNE_ADAUGA_SULF,
    ACTIUNE_ALERTA_INGHET,
    ACTIUNE_OK,
    ACTIUNE_OPRESTE_IRIGARE,
    ACTIUNE_PORNESTE_IRIGARE,
    decide,
)
from app.schemas import SenzorIn


def make(**kw) -> SenzorIn:
    base = {"lat": 46.77, "lon": 23.62, "ph": 6.5, "umiditate": 50.0, "temperatura": 20.0}
    base.update(kw)
    return SenzorIn(**base)


def test_ok_in_limite_normale():
    res = decide(make())
    assert res.actiune == ACTIUNE_OK
    assert res.alerta is False
    assert res.ph_status == "OPTIM"


def test_porneste_irigarea_la_umiditate_scazuta():
    res = decide(make(umiditate=20))
    assert res.actiune == ACTIUNE_PORNESTE_IRIGARE
    assert "20" in res.motiv


def test_opreste_irigarea_la_umiditate_ridicata():
    res = decide(make(umiditate=85))
    assert res.actiune == ACTIUNE_OPRESTE_IRIGARE


def test_adauga_calcar_pH_acid():
    res = decide(make(ph=4.8))
    assert res.actiune == ACTIUNE_ADAUGA_CALCAR
    assert res.ph_status == "ACID"


def test_adauga_sulf_pH_alcalin():
    res = decide(make(ph=8.0))
    assert res.actiune == ACTIUNE_ADAUGA_SULF
    assert res.ph_status == "ALCALIN"


def test_alerta_inghet():
    res = decide(make(temperatura=2))
    assert res.actiune == ACTIUNE_ALERTA_INGHET
    assert res.alerta is True


def test_activeaza_racire():
    res = decide(make(temperatura=40))
    assert res.actiune == ACTIUNE_ACTIVEAZA_RACIRE
    assert res.alerta is True


def test_prioritate_alerta_termica_peste_irigare():
    """Daca temperatura e periculoasa, are prioritate fata de irigare."""
    res = decide(make(temperatura=40, umiditate=10))
    assert res.actiune == ACTIUNE_ACTIVEAZA_RACIRE
    assert res.alerta is True


@pytest.mark.parametrize("ph", [-1.0, 14.5])
def test_pH_invalid_respinge_validarea(ph):
    with pytest.raises(Exception):
        make(ph=ph)
