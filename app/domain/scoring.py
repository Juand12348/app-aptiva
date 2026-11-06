"""Reglas puras del examen: armado (10 por componente) y calificación."""

from collections import Counter, defaultdict

from app.domain.entities import ComponentScore, ExamResult, ExamToGrade, GradedAnswer, Question
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
    correct_by_component: dict[str, int] = defaultdict(int)
    total_by_component: dict[str, int] = defaultdict(int)
    for question, answer in zip(exam.questions, graded, strict=True):
        total_by_component[question.component] += 1
        correct_by_component[question.component] += answer.is_correct

    components = [
        ComponentScore(name, correct_by_component[name], total_by_component[name]) for name in sorted(total_by_component)
    ]
    return ExamResult(
        exam_id=exam.id,
        total_score=sum(c.score for c in components),
        max_score=len(exam.questions),
        components=components,
        answers=graded,
    )
