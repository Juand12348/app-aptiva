from typing import Protocol

from app.domain.entities import Student


class StudentRepository(Protocol):
    def get_by_id(self, student_id: int) -> Student | None: ...

    def get_by_email(self, email: str) -> Student | None: ...

    def add(self, full_name: str, email: str, password_hash: str) -> Student:
        """Raises ConflictError if the email is already registered."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create(self, student_id: int) -> str: ...

    def read_student_id(self, token: str) -> int:
        """Raises AuthenticationError if the token is invalid or expired."""
        ...
