from typing import Protocol

from app.domain.entities import Diagnosis, ExamResult, ExamStatus, ExamToGrade, Question, StartedExam, Student


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

    def get_status(self, exam_id: int, student_id: int) -> ExamStatus | None:
        """None if missing or owned by another student."""
        ...

    def get_result(self, exam_id: int) -> ExamResult:
        """Result of an already finished exam, rebuilt from the stored answers."""
        ...


class DiagnosisRepository(Protocol):
    def save(self, exam_id: int, diagnosis: Diagnosis) -> None:
        """Creates or replaces the exam's diagnosis."""
        ...


class DiagnosisGenerator(Protocol):
    def generate(self, result: ExamResult) -> Diagnosis:
        """Raises DiagnosisUnavailableError if the AI fails or answers something invalid."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create(self, student_id: int) -> str: ...

    def read_student_id(self, token: str) -> int:
        """Raises AuthenticationError if the token is invalid or expired."""
        ...
