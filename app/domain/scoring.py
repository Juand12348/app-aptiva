"""Reglas puras del examen: armado (10 por componente) y calificación."""

from collections import Counter, defaultdict

from app.domain.entities import (
    ComponentScore,
    DifficultyScore,
    ExamResult,
    ExamToGrade,
    GradedAnswer,
    Question,
)
from app.domain.exceptions import InvalidDataError

QUESTIONS_PER_COMPONENT = 10
EXAM_SIZE = 30


def arrange_exam(questions: list[Question]) -> list[Question]:
    """Valida la composición y agrupa por componente (el orden dentro de cada uno se conserva)."""
    if len({q.id for q in questions}) != len(questions):
        raise ValueError("El examen tiene preguntas repetidas")
    per_component = Counter(q.component for q in questions)
    if len(questions) != EXAM_SIZE or any(n != QUESTIONS_PER_COMPONENT for n in per_component.values()):
        # Falla del banco, no del estudiante: debe verse como error del servidor.
        raise ValueError(f"El banco no permite armar un examen de 10 por componente: {dict(per_component)}")
    return sorted(questions, key=lambda q: q.component)  # sorted es estable


def grade_exam(exam: ExamToGrade, answers: dict[int, int]) -> ExamResult:
    """Califica. `answers` es {id_pregunta: id_opcion}; una pregunta sin responder cuenta como incorrecta."""
    questions = {q.id: q for q in exam.questions}
    for question_id, option_id in answers.items():
        if question_id not in questions:
            raise InvalidDataError(f"La pregunta {question_id} no pertenece a este examen")
        if option_id not in questions[question_id].option_ids:
            raise InvalidDataError(f"La opción {option_id} no pertenece a la pregunta {question_id}")

    graded = [
        GradedAnswer(q.id, answers.get(q.id), answers.get(q.id) == q.correct_option_id) for q in exam.questions
    ]
    return summarize(exam.id, [(q.component, q.difficulty) for q in exam.questions], graded)


def summarize(exam_id: int, labels: list[tuple[str, str]], graded: list[GradedAnswer]) -> ExamResult:
    """Puntaje global, por componente y por dificultad. `labels[i]` = (componente, dificultad) de `graded[i]`."""
    # tally[componente][dificultad] = [correctas, total]
    tally: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (component, difficulty), answer in zip(labels, graded, strict=True):
        cell = tally[component][difficulty]
        cell[0] += answer.is_correct
        cell[1] += 1

    components = [
        ComponentScore(
            component=component,
            score=sum(correct for correct, _ in by_level.values()),
            max_score=sum(total for _, total in by_level.values()),
            by_difficulty=[DifficultyScore(level, *by_level[level]) for level in sorted(by_level)],
        )
        for component, by_level in sorted(tally.items())
    ]
    return ExamResult(
        exam_id=exam_id,
        total_score=sum(c.score for c in components),
        max_score=len(graded),
        components=components,
        answers=graded,
    )
