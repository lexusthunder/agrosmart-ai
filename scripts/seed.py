"""Populeaza DB cu un utilizator demo si cateva citiri exemplu."""

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
DEMO_PASSWORD = "agrosmart2025"  # noqa: S105
DEMO_EMAIL = "fermier@agrosmart.ro"


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


def seed_readings(session: Session, user: User, n: int = 25) -> None:
    existing = session.exec(select(SenzorDate)).first()
    if existing:
        print(f"  • Citiri deja existente — skip seed")
        return

    rng = random.Random(42)
    base_lat, base_lon = 46.77, 23.62  # Cluj-Napoca
    now = datetime.utcnow()

    for i in range(n):
        date = SenzorIn(
            lat=base_lat + rng.uniform(-0.02, 0.02),
            lon=base_lon + rng.uniform(-0.02, 0.02),
            ph=round(rng.uniform(4.5, 8.5), 2),
            umiditate=round(rng.uniform(15, 95), 1),
            temperatura=round(rng.uniform(-2, 40), 1),
        )
        decizie = decide(date)
        rec = SenzorDate(
            **date.model_dump(),
            actiune=decizie.actiune,
            motiv=decizie.motiv,
            alerta=decizie.alerta,
            timestamp=now - timedelta(hours=i * 2),
            user_id=user.id,
        )
        session.add(rec)
    session.commit()
    print(f"  ✓ Inserate {n} citiri demo")


def main() -> None:
    print("Seed AgroSmart AI...")
    init_db()
    with Session(engine) as session:
        user = seed_user(session)
        seed_readings(session, user)
    print("Gata!")


if __name__ == "__main__":
    main()
