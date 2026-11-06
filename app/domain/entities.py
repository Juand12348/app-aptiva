from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True)
class Student:
    id: int
    full_name: str
    email: str
    password_hash: str


class ExamStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass(frozen=True)
class Option:
    id: int
    text: str


@dataclass(frozen=True)
class Question:
    """Pregunta tal como la ve el estudiante: no lleva la respuesta correcta."""

    id: int
    component_id: int
    component: str
    difficulty: str
    statement: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class StartedExam:
    id: int
    started_at: datetime
    questions: list[Question]  # en orden de presentación (posición 1..30)


@dataclass(frozen=True)
class GradableQuestion:
    id: int
    component: str
    difficulty: str
    option_ids: frozenset[int]
    correct_option_id: int


@dataclass(frozen=True)
class ExamToGrade:
    id: int
    status: ExamStatus
    questions: list[GradableQuestion]


@dataclass(frozen=True)
class GradedAnswer:
    question_id: int
    selected_option_id: int | None
    is_correct: bool


@dataclass(frozen=True)
class DifficultyScore:
    difficulty: str
    correct: int
    total: int


@dataclass(frozen=True)
class ComponentScore:
    component: str
    score: int
    max_score: int
    by_difficulty: list[DifficultyScore]


@dataclass(frozen=True)
class ExamResult:
    exam_id: int
    total_score: int
    max_score: int
    components: list[ComponentScore]
    answers: list[GradedAnswer]


@dataclass(frozen=True)
class Diagnosis:
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


@dataclass(frozen=True)
class SubmittedExam:
    result: ExamResult
    diagnosis: Diagnosis | None  # None si Gemini falló: los puntajes ya quedaron guardados
