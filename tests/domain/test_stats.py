from datetime import UTC, datetime

from app.domain.entities import ExamHistoryItem, GradedAnswer
from app.domain.scoring import summarize
from app.domain.stats import build_stats

LABELS = [(component, "Fácil") for component in "ABC" for _ in range(10)]


def item(exam_id: int, day: int, correct_at: set[int]) -> ExamHistoryItem:
    """`correct_at`: índices 0..29 (posición - 1) respondidos bien."""
    graded = [GradedAnswer(i, 1, i in correct_at) for i in range(30)]
    when = datetime(2026, 11, day, tzinfo=UTC)
    return ExamHistoryItem(when, when, summarize(exam_id, LABELS, graded), has_diagnosis=False)


def test_build_stats_with_no_exams_is_empty() -> None:
    stats = build_stats([])
    assert stats.exams_count == 0
    assert stats.evolution == stats.components == stats.by_difficulty == stats.by_position_in_block == []


def test_build_stats_aggregates_history() -> None:
    older = item(1, 1, {i for i in range(30) if i % 10 >= 5})  # solo acierta la segunda mitad de cada bloque
    newer = item(2, 2, set(range(30)))  # todo bien
    stats = build_stats([newer, older])  # el repositorio entrega el más reciente primero

    assert stats.exams_count == 2
    assert [(p.exam_id, p.total_score) for p in stats.evolution] == [(1, 15), (2, 30)]  # antiguo → reciente
    assert stats.evolution[0].component_scores == {"A": 5, "B": 5, "C": 5}
    assert [(c.component, c.average_score, c.latest_score, c.max_score) for c in stats.components] == [
        ("A", 7.5, 10, 10), ("B", 7.5, 10, 10), ("C", 7.5, 10, 10),
    ]
    assert [(a.label, a.correct, a.total, a.accuracy) for a in stats.by_difficulty] == [("Fácil", 45, 60, 0.75)]
    assert [(a.correct, a.total) for a in stats.components[0].by_difficulty] == [(15, 20)]
    # Primera mitad del bloque: 0 + 15 aciertos; segunda mitad: 15 + 15.
    assert [(a.label, a.correct, a.total) for a in stats.by_position_in_block] == [("1-5", 15, 30), ("6-10", 30, 30)]
