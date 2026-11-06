import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.exceptions import AuthenticationError, ConflictError, DomainError, InvalidDataError, NotFoundError
from app.presentation.errors import register_error_handlers


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(NotFoundError, 404), (ConflictError, 409), (InvalidDataError, 422), (AuthenticationError, 401)],
)
def test_domain_errors_map_to_http(error: type[DomainError], expected_status: int) -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise error("Mensaje de prueba")

    response = TestClient(app).get("/boom")
    assert response.status_code == expected_status
    assert response.json() == {"detail": "Mensaje de prueba"}


@pytest.mark.parametrize(
    ("path", "kwargs", "expected"),
    [
        ("/api/v1/auth/register", {"json": {}},
         "El campo nombre es obligatorio; El campo correo es obligatorio; El campo contraseña es obligatorio"),
        ("/api/v1/auth/register", {"json": {"full_name": "A", "email": "x", "password": "12345678"}},
         "El campo correo no tiene un formato válido"),
        ("/api/v1/auth/register", {"json": {"full_name": "A", "email": "a@a.co", "password": "1"}},
         "El campo contraseña debe tener al menos 8 caracteres"),
        ("/api/v1/auth/register", {"content": "{malo", "headers": {"content-type": "application/json"}},
         "El cuerpo de la petición no es un JSON válido"),
        ("/api/v1/auth/login", {"data": {"username": "a@a.co"}}, "El campo contraseña es obligatorio"),
        ("/api/v1/exams/1/submit", {"json": {"answers": [{"question_id": 1, "option_id": 1}] * 31}},
         "El campo respuestas admite como máximo 30 elementos"),
        ("/api/v1/exams/1/submit", {"json": {"answers": [{"question_id": "x", "option_id": 1}]}},
         "El campo id de la pregunta debe ser un número entero"),
    ],
)
def test_validation_errors_are_a_spanish_string(path: str, kwargs: dict, expected: str) -> None:
    from app.domain.entities import Student
    from app.main import app
    from app.presentation.dependencies import get_current_student

    app.dependency_overrides[get_current_student] = lambda: Student(1, "Ana", "ana@correo.com", "hash")
    try:
        response = TestClient(app).post(path, **kwargs)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json() == {"detail": expected}
