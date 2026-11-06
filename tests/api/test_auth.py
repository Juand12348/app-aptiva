from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.security import JwtTokenService
from app.main import app
from app.presentation.dependencies import get_student_repository
from tests.fakes import InMemoryStudentRepository

SECRET = "test-secret-key-de-al-menos-32-caracteres"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/students/me"


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = InMemoryStudentRepository()
    app.dependency_overrides[get_student_repository] = lambda: repository
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client: TestClient, email: str = "Ana@Correo.com ", password: str = "clave-segura") -> dict:
    return client.post(REGISTER, json={"full_name": "Ana Pérez", "email": email, "password": password}).json()


def login(client: TestClient, email: str = "ana@correo.com", password: str = "clave-segura"):  # noqa: ANN201
    return client.post(LOGIN, data={"username": email, "password": password})


def test_register_normalizes_email_and_hides_password(client: TestClient) -> None:
    response = client.post(REGISTER, json={"full_name": " Ana Pérez ", "email": "Ana@Correo.com", "password": "clave-segura"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "full_name": "Ana Pérez", "email": "ana@correo.com"}


def test_register_duplicate_email_is_409(client: TestClient) -> None:
    register(client)
    response = client.post(REGISTER, json={"full_name": "Otra", "email": "ANA@correo.com", "password": "otra-clave"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe una cuenta con ese correo"}


@pytest.mark.parametrize(
    "body",
    [
        {"full_name": "Ana", "email": "ana@correo.com", "password": "corta"},
        {"full_name": "Ana", "email": "no-es-correo", "password": "clave-segura"},
        {"full_name": "", "email": "ana@correo.com", "password": "clave-segura"},
    ],
)
def test_register_rejects_invalid_input(client: TestClient, body: dict) -> None:
    assert client.post(REGISTER, json=body).status_code == 422


def test_login_then_me(client: TestClient) -> None:
    register(client)
    response = login(client, email="ANA@correo.com")
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

    me = client.get(ME, headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ana@correo.com"


@pytest.mark.parametrize(("email", "password"), [("ana@correo.com", "clave-mala"), ("nadie@correo.com", "clave-segura")])
def test_login_bad_credentials_is_401_with_generic_message(client: TestClient, email: str, password: str) -> None:
    register(client)
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Correo o contraseña incorrectos"}


def test_me_without_token_is_401(client: TestClient) -> None:
    assert client.get(ME).status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "no-es-un-jwt",
        JwtTokenService(SECRET, expire_minutes=-1).create(1),  # vencido
        JwtTokenService("otro-secreto-distinto-de-al-menos-32-chars", 60).create(1),  # firma ajena
        JwtTokenService(SECRET, 60).create(999),  # estudiante inexistente
    ],
)
def test_me_with_invalid_token_is_401(client: TestClient, token: str) -> None:
    register(client)
    response = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido o vencido"}
