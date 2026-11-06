from typing import Protocol

from app.domain.entities import ExamResult, ExamToGrade, Question, StartedExam, Student


class StudentRepository(Protocol):
    def get_by_id(self, student_id: int) -> Student | None: ...

    def get_by_email(self, email: str) -> Student | None: ...

    def add(self, full_name: str, email: str, password_hash: str) -> Student:
        """Raises ConflictError if the email is already registered."""
        ...


class QuestionRepository(Protocol):
    def pick_random(self, per_component: int) -> list[Question]:
        """Active questions chosen at random, `per_component` from each component."""
        ...


class ExamRepository(Protocol):
    def create(self, student_id: int, questions: list[Question]) -> StartedExam:
        """Stores the exam with its questions in the given order (positions 1..n)."""
        ...

    def get_for_grading(self, exam_id: int, student_id: int) -> ExamToGrade | None:
        """Locks the exam row until the transaction ends. None if missing or owned by another student."""
        ...

    def save_result(self, result: ExamResult) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create(self, student_id: int) -> str: ...

    def read_student_id(self, token: str) -> int:
        """Raises AuthenticationError if the token is invalid or expired."""
        ...
