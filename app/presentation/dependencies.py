"""Único punto donde la presentación se conecta con la infraestructura."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.application.auth import GetCurrentStudent, Login, RegisterStudent
from app.domain.entities import Student
from app.domain.exceptions import AuthenticationError
from app.domain.ports import StudentRepository, TokenService
from app.infrastructure.config import get_settings
from app.infrastructure.database import get_session, is_database_reachable
from app.infrastructure.repositories import SqlStudentRepository
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService

__all__ = ["get_current_student", "get_login", "get_register_student", "is_database_reachable"]

password_hasher = Argon2PasswordHasher()
# auto_error=False: el 401 sale de nuestro manejador, con mensaje en español.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_student_repository(session: Session = Depends(get_session)) -> StudentRepository:
    return SqlStudentRepository(session)


def get_token_service() -> TokenService:
    settings = get_settings()
    return JwtTokenService(settings.jwt_secret_key, settings.access_token_expire_minutes)


def get_register_student(students: StudentRepository = Depends(get_student_repository)) -> RegisterStudent:
    return RegisterStudent(students, password_hasher)


def get_login(
    students: StudentRepository = Depends(get_student_repository),
    tokens: TokenService = Depends(get_token_service),
) -> Login:
    return Login(students, password_hasher, tokens)


def get_current_student(
    token: str | None = Depends(oauth2_scheme),
    students: StudentRepository = Depends(get_student_repository),
    tokens: TokenService = Depends(get_token_service),
) -> Student:
    if token is None:
        raise AuthenticationError("No autenticado")
    return GetCurrentStudent(students, tokens).execute(token)
