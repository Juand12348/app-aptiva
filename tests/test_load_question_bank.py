import random

from scripts.load_question_bank import read_questions, shuffled_options, validate_questions


def make_question(**overrides: object) -> dict:
    question = {"id": 1, "componente": "Geometria", "nivel": "Básico", "pregunta": "¿2+2?",
                "opciones": ["1", "2", "3", "4"], "correcta": "4"}
    return question | overrides


def test_real_data_files_are_valid() -> None:
    assert validate_questions(read_questions()) == []


def test_rejects_invalid_questions() -> None:
    bad = [
        make_question(id=1, opciones=["1", "2", "4"]),
        make_question(id=2, opciones=["4", "2", "3", "4"]),
        make_question(id=3, correcta="5"),
        make_question(id=4, nivel="Experto"),
        make_question(id=5, componente="Física"),
    ]
    errors = validate_questions(bad)
    for question_id in range(1, 6):
        assert any(f"id={question_id}:" in error for error in errors)
    assert any("se requieren 50" in error for error in errors)


def test_shuffle_keeps_exactly_one_correct_option() -> None:
    options = shuffled_options(make_question(), random.Random(0))
    assert sorted(text for text, _ in options) == ["1", "2", "3", "4"]
    assert [text for text, correct in options if correct] == ["4"]
