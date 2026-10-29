import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.core import database
from backend.scripts.seed_db import seed_database

# Use in-memory SQLite with StaticPool so all connections share the exact same in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    database.engine = test_engine
    database.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=test_engine)
    test_db = TestingSessionLocal()
    seed_database(db_session=test_db)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def institution_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "inst1@aicte.gov.in", "password": "Demo@Password123"}
    )
    return res.json()["access_token"]

@pytest.fixture
def official_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "official@aicte.gov.in", "password": "Demo@Password123"}
    )
    return res.json()["access_token"]

@pytest.fixture
def admin_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aicte.gov.in", "password": "Demo@Password123"}
    )
    return res.json()["access_token"]

@pytest.fixture
def auditor_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor@aicte.gov.in", "password": "Demo@Password123"}
    )
    return res.json()["access_token"]

