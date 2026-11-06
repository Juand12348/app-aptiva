from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.domain.entities import Student
from app.main import app
from app.presentation.dependencies import get_current_student, get_exam_repository, get_question_repository
from tests.fakes import FakeQuestionRepository, InMemoryExamRepository, make_bank

EXAMS = "/api/v1/exams"
ANA = Student(1, "Ana", "ana@correo.com", "hash")
LUIS = Student(2, "Luis", "luis@correo.com", "hash")


@pytest.fixture
def setup() -> Iterator[tuple[TestClient, dict[int, int]]]:
    questions, correct = make_bank()
    exams = InMemoryExamRepository(correct)
    app.dependency_overrides[get_question_repository] = lambda: FakeQuestionRepository(questions)
    app.dependency_overrides[get_exam_repository] = lambda: exams
    app.dependency_overrides[get_current_student] = lambda: ANA
    yield TestClient(app), correct
    app.dependency_overrides.clear()


def start(client: TestClient) -> dict:
    response = client.post(EXAMS)
    assert response.status_code == 201
    return response.json()


def submit(client: TestClient, exam_id: int, answers: list[tuple[int, int]]):  # noqa: ANN201
    body = {"answers": [{"question_id": q, "option_id": o} for q, o in answers]}
    return client.post(f"{EXAMS}/{exam_id}/submit", json=body)


def test_start_exam_returns_30_questions_10_per_component(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    questions = exam["questions"]
    assert len(questions) == 30
    assert len({q["question_id"] for q in questions}) == 30
    assert [q["position"] for q in questions] == list(range(1, 31))
    components = [q["component"] for q in questions]
    assert {components.count(c) for c in set(components)} == {10}
    assert all(len(q["options"]) == 4 for q in questions)


def test_start_exam_never_exposes_correct_answer(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    response = client.post(EXAMS)
    assert "correct" not in response.text.lower()
    assert set(response.json()["questions"][0]["options"][0]) == {"option_id", "text"}


def test_submit_all_correct_scores_30(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, correct = setup
    exam = start(client)
    response = submit(client, exam["exam_id"], [(q["question_id"], correct[q["question_id"]]) for q in exam["questions"]])
    assert response.status_code == 200
    body = response.json()
    assert (body["total_score"], body["max_score"]) == (30, 30)
    assert [(c["score"], c["max_score"]) for c in body["components"]] == [(10, 10)] * 3


def test_submit_partial_answers_unanswered_count_as_wrong(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, correct = setup
    exam = start(client)
    first = exam["questions"][0]  # bloque del primer componente
    wrong_option = next(o["option_id"] for o in first["options"] if o["option_id"] != correct[first["question_id"]])
    second = exam["questions"][1]
    response = submit(client, exam["exam_id"], [(first["question_id"], wrong_option), (second["question_id"], correct[second["question_id"]])])
    body = response.json()
    assert body["total_score"] == 1
    assert body["components"][[c["component"] for c in body["components"]].index(first["component"])]["score"] == 1


def test_submit_twice_is_409(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    assert submit(client, exam["exam_id"], []).status_code == 200
    response = submit(client, exam["exam_id"], [])
    assert response.status_code == 409
    assert response.json() == {"detail": "El examen ya fue enviado"}


def test_submit_other_students_exam_is_404(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    app.dependency_overrides[get_current_student] = lambda: LUIS
    assert submit(client, exam["exam_id"], []).status_code == 404
    assert submit(client, 999, []).json() == {"detail": "Examen no encontrado"}


def test_submit_rejects_invalid_answers(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    q1, q2 = exam["questions"][0], exam["questions"][1]
    foreign_option = q2["options"][0]["option_id"]
    assert submit(client, exam["exam_id"], [(q1["question_id"], foreign_option)]).status_code == 422
    assert submit(client, exam["exam_id"], [(99999, 1)]).status_code == 422
    duplicated = [(q1["question_id"], q1["options"][0]["option_id"])] * 2
    assert submit(client, exam["exam_id"], duplicated).json() == {"detail": "Hay preguntas respondidas más de una vez"}
    # Las respuestas inválidas no consumen el envío: el examen sigue abierto.
    assert submit(client, exam["exam_id"], []).status_code == 200


def test_exams_require_token(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    del app.dependency_overrides[get_current_student]
    assert client.post(EXAMS).status_code == 401
    assert submit(client, 1, []).status_code == 401
