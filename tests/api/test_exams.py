from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.domain.entities import Student
from app.main import app
from app.presentation.dependencies import (
    get_current_student,
    get_diagnosis_generator,
    get_diagnosis_repository,
    get_exam_repository,
    get_question_repository,
)
from tests.fakes import (
    FakeDiagnosisGenerator,
    FakeQuestionRepository,
    InMemoryDiagnosisRepository,
    InMemoryExamRepository,
    make_bank,
)

EXAMS = "/api/v1/exams"
ANA = Student(1, "Ana", "ana@correo.com", "hash")
LUIS = Student(2, "Luis", "luis@correo.com", "hash")


@pytest.fixture
def generator() -> FakeDiagnosisGenerator:
    return FakeDiagnosisGenerator()


@pytest.fixture
def diagnoses() -> InMemoryDiagnosisRepository:
    return InMemoryDiagnosisRepository()


@pytest.fixture
def setup(
    generator: FakeDiagnosisGenerator, diagnoses: InMemoryDiagnosisRepository
) -> Iterator[tuple[TestClient, dict[int, int]]]:
    questions, correct = make_bank()
    exams = InMemoryExamRepository(correct, diagnoses)
    app.dependency_overrides[get_question_repository] = lambda: FakeQuestionRepository(questions)
    app.dependency_overrides[get_exam_repository] = lambda: exams
    app.dependency_overrides[get_diagnosis_generator] = lambda: generator
    app.dependency_overrides[get_diagnosis_repository] = lambda: diagnoses
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


def all_correct(exam: dict, correct: dict[int, int]) -> list[tuple[int, int]]:
    return [(q["question_id"], correct[q["question_id"]]) for q in exam["questions"]]


def test_submit_returns_diagnosis_and_by_difficulty(
    setup: tuple[TestClient, dict[int, int]], diagnoses: InMemoryDiagnosisRepository
) -> None:
    client, correct = setup
    exam = start(client)
    body = submit(client, exam["exam_id"], all_correct(exam, correct)).json()
    assert body["diagnosis"]["recommendations"] == ["Repasa probabilidad", "Practica", "Revisa"]
    assert exam["exam_id"] in diagnoses.saved
    levels = body["components"][0]["by_difficulty"]
    assert sum(level["total"] for level in levels) == 10
    assert all(level["correct"] == level["total"] for level in levels)


def test_gemini_failure_keeps_scores_and_diagnosis_is_null(
    setup: tuple[TestClient, dict[int, int]], generator: FakeDiagnosisGenerator
) -> None:
    client, correct = setup
    generator.fail = True
    exam = start(client)
    response = submit(client, exam["exam_id"], all_correct(exam, correct))
    assert response.status_code == 200
    assert response.json()["total_score"] == 30
    assert response.json()["diagnosis"] is None
    # El examen quedó cerrado con su puntaje: no se puede reenviar.
    assert submit(client, exam["exam_id"], []).status_code == 409


def test_regenerate_diagnosis_after_failure(
    setup: tuple[TestClient, dict[int, int]], generator: FakeDiagnosisGenerator
) -> None:
    client, _ = setup
    generator.fail = True
    exam = start(client)
    submit(client, exam["exam_id"], [])
    response = client.post(f"{EXAMS}/{exam['exam_id']}/diagnosis")
    assert response.status_code == 503
    assert response.json() == {"detail": "No se pudo contactar a Gemini"}

    generator.fail = False
    response = client.post(f"{EXAMS}/{exam['exam_id']}/diagnosis")
    assert response.status_code == 200
    assert set(response.json()) == {"strengths", "weaknesses", "recommendations"}
    assert generator.calls[-1].total_score == 0  # regenera con los puntajes guardados


def test_regenerate_diagnosis_errors(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    response = client.post(f"{EXAMS}/{exam['exam_id']}/diagnosis")
    assert response.status_code == 409
    assert response.json() == {"detail": "El examen aún no ha sido enviado"}
    assert client.post(f"{EXAMS}/999/diagnosis").status_code == 404
    app.dependency_overrides[get_current_student] = lambda: LUIS
    assert client.post(f"{EXAMS}/{exam['exam_id']}/diagnosis").status_code == 404


def test_result_matches_submit_response(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, correct = setup
    exam = start(client)
    submitted = submit(client, exam["exam_id"], all_correct(exam, correct)[:12]).json()
    response = client.get(f"{EXAMS}/{exam['exam_id']}/result")
    assert response.status_code == 200
    assert response.json() == submitted


def test_result_shows_regenerated_diagnosis(
    setup: tuple[TestClient, dict[int, int]], generator: FakeDiagnosisGenerator
) -> None:
    client, _ = setup
    generator.fail = True
    exam = start(client)
    submit(client, exam["exam_id"], [])
    assert client.get(f"{EXAMS}/{exam['exam_id']}/result").json()["diagnosis"] is None
    generator.fail = False
    client.post(f"{EXAMS}/{exam['exam_id']}/diagnosis")
    assert client.get(f"{EXAMS}/{exam['exam_id']}/result").json()["diagnosis"] is not None


def test_result_errors(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    response = client.get(f"{EXAMS}/{exam['exam_id']}/result")
    assert response.status_code == 409
    assert response.json() == {"detail": "El examen aún no ha sido enviado"}
    assert client.get(f"{EXAMS}/999/result").status_code == 404
    submit(client, exam["exam_id"], [])
    app.dependency_overrides[get_current_student] = lambda: LUIS
    assert client.get(f"{EXAMS}/{exam['exam_id']}/result").status_code == 404


def test_history_lists_only_finished_exams_newest_first(
    setup: tuple[TestClient, dict[int, int]], generator: FakeDiagnosisGenerator
) -> None:
    client, correct = setup
    first = start(client)
    submit(client, first["exam_id"], all_correct(first, correct))
    generator.fail = True
    second = start(client)
    submit(client, second["exam_id"], [])
    start(client)  # en curso: no aparece en el historial

    response = client.get("/api/v1/students/me/exams")
    assert response.status_code == 200
    history = response.json()
    assert [item["exam_id"] for item in history] == [second["exam_id"], first["exam_id"]]
    assert [item["total_score"] for item in history] == [0, 30]
    assert [item["has_diagnosis"] for item in history] == [False, True]
    assert history[1]["finished_at"] >= history[1]["started_at"]
    assert [c["score"] for c in history[1]["components"]] == [10, 10, 10]


def test_history_is_per_student(setup: tuple[TestClient, dict[int, int]]) -> None:
    client, _ = setup
    exam = start(client)
    submit(client, exam["exam_id"], [])
    app.dependency_overrides[get_current_student] = lambda: LUIS
    assert client.get("/api/v1/students/me/exams").json() == []
    del app.dependency_overrides[get_current_student]
    assert client.get("/api/v1/students/me/exams").status_code == 401
