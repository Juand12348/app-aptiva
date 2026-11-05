from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.main import app
from app.presentation.dependencies import is_database_reachable

client = TestClient(app)


def test_health_ok_when_database_reachable() -> None:
    app.dependency_overrides[is_database_reachable] = lambda: True
    response = client.get("/health")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_database_unavailable() -> None:
    app.dependency_overrides[is_database_reachable] = lambda: False
    response = client.get("/health")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_swagger_available() -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Aptiva AI"


def test_cors_allows_streamlit_origin() -> None:
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:8501", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:8501"


def test_database_url_normalized_to_psycopg() -> None:
    settings = Settings(database_url="postgresql://u:p@h/db?sslmode=require")
    assert settings.database_url == "postgresql+psycopg://u:p@h/db?sslmode=require"
