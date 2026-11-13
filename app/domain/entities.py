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
    expires_at: datetime | None = None  # lo fija StartExam; el repositorio no lo conoce


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


@dataclass(frozen=True)
class ExamHistoryItem:
    started_at: datetime
    finished_at: datetime
    result: ExamResult
    has_diagnosis: bool


@dataclass(frozen=True)
class Accuracy:
    label: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return round(self.correct / self.total, 2)


@dataclass(frozen=True)
class EvolutionPoint:
    exam_id: int
    finished_at: datetime
    total_score: int
    max_score: int
    component_scores: dict[str, int]


@dataclass(frozen=True)
class ComponentStats:
    component: str
    average_score: float
    latest_score: int
    max_score: int
    by_difficulty: list[Accuracy]


@dataclass(frozen=True)
class StudentStats:
    exams_count: int
    evolution: list[EvolutionPoint]  # del más antiguo al más reciente
    components: list[ComponentStats]
    by_difficulty: list[Accuracy]
    by_position_in_block: list[Accuracy]
