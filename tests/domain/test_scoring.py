import pytest

from app.domain.entities import ExamStatus, ExamToGrade, GradableQuestion
from app.domain.exceptions import InvalidDataError
from app.domain.scoring import arrange_exam, grade_exam
from tests.fakes import FakeQuestionRepository, make_bank


def test_arrange_exam_groups_10_per_component() -> None:
    questions, _ = make_bank()
    arranged = arrange_exam(FakeQuestionRepository(questions).pick_random(10))
    assert len(arranged) == 30
    assert len({q.id for q in arranged}) == 30
    components = [q.component for q in arranged]
    assert components == sorted(components)  # agrupadas, cada componente en un bloque
    assert {components.count(c) for c in set(components)} == {10}


def test_arrange_exam_rejects_insufficient_bank() -> None:
    questions, _ = make_bank(per_component=9)
    with pytest.raises(ValueError, match="10 por componente"):
        arrange_exam(FakeQuestionRepository(questions).pick_random(10))


def test_arrange_exam_rejects_repeated_questions() -> None:
    questions, _ = make_bank(per_component=10)
    with pytest.raises(ValueError, match="repetidas"):
        arrange_exam(questions[:29] + [questions[0]])


def exam_with(components: list[str]) -> ExamToGrade:
    return ExamToGrade(
        1,
        ExamStatus.IN_PROGRESS,
        [GradableQuestion(i, c, "Fácil", frozenset({i * 10, i * 10 + 1}), i * 10 + 1) for i, c in enumerate(components, 1)],
    )


def test_grade_counts_unanswered_as_incorrect_and_scores_by_component() -> None:
    exam = exam_with(["A", "A", "B", "B"])
    result = grade_exam(exam, {1: 11, 2: 20, 3: 31})  # 1 bien, 2 mal, 3 bien, 4 sin responder
    assert result.total_score == 2
    assert result.max_score == 4
    assert [(c.component, c.score, c.max_score) for c in result.components] == [("A", 1, 2), ("B", 1, 2)]
    assert [(d.difficulty, d.correct, d.total) for d in result.components[0].by_difficulty] == [("Fácil", 1, 2)]
    assert [a.is_correct for a in result.answers] == [True, False, True, False]
    assert result.answers[3].selected_option_id is None


@pytest.mark.parametrize(("answers", "message"), [({99: 990}, "pregunta 99"), ({1: 20}, "opción 20")])
def test_grade_rejects_foreign_question_or_option(answers: dict[int, int], message: str) -> None:
    with pytest.raises(InvalidDataError, match=message):
        grade_exam(exam_with(["A", "B"]), answers)
