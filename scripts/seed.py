"""Populeaza DB cu un utilizator demo si citiri exemplu raspandite pe toata Romania."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.database import engine, init_db
from app.decision import decide
from app.models import SenzorDate, User
from app.schemas import SenzorIn
from app.security import hash_password

DEMO_USERNAME = "fermier"
DEMO_PASSWORD = "agrosmart2025"
DEMO_EMAIL = "fermier@agrosmart.ro"

# Ferme demo raspandite pe toata Romania pentru harta convingatoare
FERME = [
    ("Cluj-Napoca",  46.77, 23.62),
    ("Bucuresti",    44.43, 26.10),
    ("Iasi",         47.16, 27.59),
    ("Timisoara",    45.75, 21.23),
    ("Constanta",    44.18, 28.65),
    ("Brasov",       45.66, 25.61),
    ("Sibiu",        45.79, 24.15),
    ("Galati",       45.43, 28.05),
    ("Oradea",       47.05, 21.93),
    ("Suceava",      47.65, 26.25),
    ("Targu Mures",  46.55, 24.56),
    ("Pitesti",      44.85, 24.87),
]


def seed_user(session: Session) -> User:
    user = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if user:
        print(f"  • User '{DEMO_USERNAME}' deja existent (id={user.id})")
        return user
    user = User(
        username=DEMO_USERNAME,
        email=DEMO_EMAIL,
        full_name="Fermier Demo",
        hashed_password=hash_password(DEMO_PASSWORD),
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"  ✓ Creat user '{DEMO_USERNAME}' (parola: {DEMO_PASSWORD})")
    return user


def seed_readings(session: Session, user: User, per_ferma: int = 4) -> None:
    existing = session.exec(select(SenzorDate)).first()
    if existing:
        print("  • Citiri deja existente — skip seed")
        return

    rng = random.Random(42)
    now = datetime.utcnow()
    total = 0

    # Mix de scenarii: ~70% normal, ~20% actiuni, ~10% alerte (pentru harta colorata)
    scenarios = [
        # (ph_range, umid_range, temp_range, weight)
        ((6.0, 7.2),  (50, 75), (18, 26), 7),  # normal
        ((5.5, 6.0),  (28, 35), (28, 32), 2),  # umiditate scazuta -> irigare
        ((4.0, 4.8),  (40, 60), (15, 25), 1),  # pH foarte acid -> alerta
        ((7.8, 8.5),  (40, 60), (35, 42), 1),  # pH alcalin + temp mare -> alerta
        ((6.0, 7.0),  (88, 96), (22, 28), 1),  # umiditate excesiva
    ]
    pool = []
    for sc, w in scenarios:
        pool.extend([sc] * w)

    for nume, base_lat, base_lon in FERME:
        for i in range(per_ferma):
            ph_r, um_r, t_r = rng.choice(pool)
            date = SenzorIn(
                lat=base_lat + rng.uniform(-0.04, 0.04),
                lon=base_lon + rng.uniform(-0.04, 0.04),
                ph=round(rng.uniform(*ph_r), 2),
                umiditate=round(rng.uniform(*um_r), 1),
                temperatura=round(rng.uniform(*t_r), 1),
            )
            decizie = decide(date)
            rec = SenzorDate(
                **date.model_dump(),
                actiune=decizie.actiune,
                motiv=decizie.motiv,
                alerta=decizie.alerta,
                timestamp=now - timedelta(hours=rng.randint(0, 7 * 24)),
                user_id=user.id,
            )
            session.add(rec)
            total += 1
    session.commit()
    print(f"  ✓ Inserate {total} citiri demo pe {len(FERME)} ferme din Romania")


def main() -> None:
    print("Seed AgroSmart AI...")
    init_db()
    with Session(engine) as session:
        user = seed_user(session)
        seed_readings(session, user)
    print("Gata!")


if __name__ == "__main__":
    main()
