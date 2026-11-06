from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DiagnosisUnavailableError,
    DomainError,
    InvalidDataError,
    NotFoundError,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidDataError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    DiagnosisUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}

FIELD_NAMES = {
    "full_name": "nombre",
    "email": "correo",
    "username": "correo",
    "password": "contraseña",
    "answers": "respuestas",
    "exam_id": "id del examen",
    "question_id": "id de la pregunta",
    "option_id": "id de la opción",
}

MESSAGES = {
    "missing": "El campo {field} es obligatorio",
    "string_too_short": "El campo {field} debe tener al menos {min_length} caracteres",
    "string_too_long": "El campo {field} admite como máximo {max_length} caracteres",
    "string_pattern_mismatch": "El campo {field} no tiene un formato válido",
    "int_parsing": "El campo {field} debe ser un número entero",
    "int_type": "El campo {field} debe ser un número entero",
    "string_type": "El campo {field} debe ser texto",
    "list_type": "El campo {field} debe ser una lista",
    "too_long": "El campo {field} admite como máximo {max_length} elementos",
    "json_invalid": "El cuerpo de la petición no es un JSON válido",
}


def to_spanish(error: dict) -> str:
    field_key = next((part for part in reversed(error["loc"]) if isinstance(part, str)), "")
    field = FIELD_NAMES.get(field_key, field_key)
    template = MESSAGES.get(error["type"], "El campo {field} no es válido")
    return template.format(field=field, **error.get("ctx", {}))


async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    # Mismo formato que los errores de dominio: {"detail": "<mensaje en español>"}.
    messages = list(dict.fromkeys(to_spanish(e) for e in error.errors()))
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "; ".join(messages)})


async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
    status_code = STATUS_BY_ERROR.get(type(error), status.HTTP_400_BAD_REQUEST)
    headers = {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(status_code=status_code, content={"detail": str(error)}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
