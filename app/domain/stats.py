"""Estadísticas del estudiante, calculadas a partir de sus exámenes finalizados."""

from collections import defaultdict

from app.domain.entities import (
    Accuracy,
    ComponentStats,
    EvolutionPoint,
    ExamHistoryItem,
    StudentStats,
)
from app.domain.scoring import QUESTIONS_PER_COMPONENT

# El examen agrupa 10 preguntas por componente, en orden aleatorio dentro de cada bloque; por eso
# comparar la mitad inicial y final del bloque separa la fatiga del efecto del componente.
HALF_BLOCK = QUESTIONS_PER_COMPONENT // 2
POSITION_LABELS = (f"1-{HALF_BLOCK}", f"{HALF_BLOCK + 1}-{QUESTIONS_PER_COMPONENT}")


def _accuracies(tally: dict[str, list[int]]) -> list[Accuracy]:
    return [Accuracy(label, correct, total) for label, (correct, total) in sorted(tally.items())]


def build_stats(history: list[ExamHistoryItem]) -> StudentStats:
    """`history` viene del más reciente al más antiguo (como lo entrega el repositorio)."""
    scores: dict[str, list[int]] = defaultdict(list)
    max_scores: dict[str, int] = {}
    latest: dict[str, int] = {}
    by_difficulty: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_component_difficulty: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    by_position: dict[str, list[int]] = {label: [0, 0] for label in POSITION_LABELS}

    for item in reversed(history):  # el último que se procesa es el más reciente
        for component in item.result.components:
            scores[component.component].append(component.score)
            max_scores[component.component] = component.max_score
            latest[component.component] = component.score
            for level in component.by_difficulty:
                for cell in (by_difficulty[level.difficulty], by_component_difficulty[component.component][level.difficulty]):
                    cell[0] += level.correct
                    cell[1] += level.total
        for index, answer in enumerate(item.result.answers):
            cell = by_position[POSITION_LABELS[0 if index % QUESTIONS_PER_COMPONENT < HALF_BLOCK else 1]]
            cell[0] += answer.is_correct
            cell[1] += 1

    return StudentStats(
        exams_count=len(history),
        evolution=[
            EvolutionPoint(
                item.result.exam_id,
                item.finished_at,
                item.result.total_score,
                item.result.max_score,
                {c.component: c.score for c in item.result.components},
            )
            for item in reversed(history)
        ],
        components=[
            ComponentStats(
                component,
                round(sum(values) / len(values), 2),
                latest[component],
                max_scores[component],
                _accuracies(by_component_difficulty[component]),
            )
            for component, values in sorted(scores.items())
        ],
        by_difficulty=_accuracies(by_difficulty),
        by_position_in_block=_accuracies(by_position) if history else [],
    )
