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
