"""Fixture-uri pytest comune."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """In-memory SQLite per test (izolare totala)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """TestClient FastAPI cu sesiunea in-memory injectata."""

    def get_session_override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(name="demo_user")
def demo_user_fixture(session: Session) -> User:
    user = User(
        username="testuser",
        email="test@agrosmart.ro",
        full_name="Test User",
        hashed_password=hash_password("testpass1234"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, demo_user: User) -> dict[str, str]:  # noqa: ARG001
    r = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass1234"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
