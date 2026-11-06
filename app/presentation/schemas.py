from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150, examples=["Ana Pérez"])
    # Validación de formato básica sin agregar la dependencia email-validator.
    email: str = Field(max_length=150, pattern=r"^\s*[^@\s]+@[^@\s]+\.[^@\s]+\s*$", examples=["ana@correo.com"])
    password: str = Field(min_length=8, max_length=128)


class StudentResponse(BaseModel):
    id: int
    full_name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
