import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main


TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)
main.Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[main.get_db] = override_get_db
client = TestClient(main.app)


def test_health_reports_model_status():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "heart" in data["models"]
    assert "diabetes" in data["models"]


def test_protected_route_requires_authentication():
    response = client.get("/profile")
    assert response.status_code == 401


def test_registration_login_screening_and_history():
    email = f"test-{uuid.uuid4().hex}@example.com"
    registration = client.post("/register", json={"email": email, "password": "safe-test-password"})
    assert registration.status_code == 200
    assert client.post("/register", json={"email": email, "password": "safe-test-password"}).status_code == 409

    login = client.post("/login", json={"email": email, "password": "safe-test-password"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == email

    screening = client.post(
        "/predict-simple",
        headers=headers,
        json={"age": 30, "glucose": 90, "bp": 115, "bmi": 22.5},
    )
    assert screening.status_code == 200
    result = screening.json()
    assert result["risk_level"] in {"Low", "Moderate", "High"}
    assert 0 <= result["risk_score"] <= 1

    heart = client.post(
        "/heart-risk",
        headers=headers,
        json={"age": 35, "sex": 1, "trestbps": 120, "chol": 190, "thalach": 160, "oldpeak": 0.2},
    )
    assert heart.status_code == 200
    assert heart.json()["risk_level"] in {"Low", "Moderate", "High"}

    diabetes = client.post(
        "/diabetes-risk",
        headers=headers,
        json={
            "pregnancies": 0, "glucose": 90, "blood_pressure": 75, "skin_thickness": 20,
            "insulin": 80, "bmi": 22.5, "diabetes_pedigree": 0.2, "age": 30,
        },
    )
    assert diabetes.status_code == 200
    assert diabetes.json()["risk_level"] in {"Low", "Moderate", "High"}

    history = client.get("/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 3
    assert {item["type"] for item in history.json()} == {"Overview", "Heart", "Diabetes"}


def test_invalid_screening_values_are_rejected():
    email = f"invalid-{uuid.uuid4().hex}@example.com"
    assert client.post(
        "/register",
        json={"email": email, "password": "safe-test-password"},
    ).status_code == 200
    login = client.post("/login", json={"email": email, "password": "safe-test-password"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post("/predict-simple", headers=headers, json={"age": 30})
    assert response.status_code == 422
