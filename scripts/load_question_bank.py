"""Carga única del banco de preguntas (data/*.json) en las tablas existentes de Neon.

Uso:
    python -m scripts.load_question_bank --dry-run   # solo valida
    python -m scripts.load_question_bank             # valida e inserta (una sola transacción)

Se niega a correr si el banco ya tiene datos, para no duplicar preguntas.
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import Connection, text

from app.infrastructure.database import engine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBJECT_NAME = "Matemáticas"
QUESTIONS_PER_COMPONENT = 50
# Los JSON usan nombres sin tilde y niveles Básico/Intermedio/Avanzado; la BD guarda los nombres del requisito.
COMPONENT_NAMES = {"Estadistica": "Estadística", "Geometria": "Geometría", "Calculo": "Cálculo y Álgebra"}
LEVEL_NAMES = {"Básico": "Fácil", "Intermedio": "Medio", "Avanzado": "Difícil"}
# Semilla fija: la mezcla de opciones es reproducible si hay que recargar.
SHUFFLE_SEED = 2026
BANK_TABLES = ["materias", "componentes", "niveles_dificultad", "preguntas", "opciones_respuesta"]


def read_questions(data_dir: Path = DATA_DIR) -> list[dict]:
    questions: list[dict] = []
    for path in sorted(data_dir.glob("*.json")):
        questions.extend(json.loads(path.read_text(encoding="utf-8")))
    return questions


def validate_questions(questions: list[dict]) -> list[str]:
    errors: list[str] = []
    for question in questions:
        ref = f"pregunta id={question.get('id')}"
        options = question.get("opciones", [])
        if question.get("componente") not in COMPONENT_NAMES:
            errors.append(f"{ref}: componente desconocido {question.get('componente')!r}")
        if question.get("nivel") not in LEVEL_NAMES:
            errors.append(f"{ref}: nivel desconocido {question.get('nivel')!r}")
        if not str(question.get("pregunta", "")).strip():
            errors.append(f"{ref}: enunciado vacío")
        if len(options) != 4 or len(set(options)) != 4:
            errors.append(f"{ref}: debe tener 4 opciones distintas")
        if options.count(question.get("correcta")) != 1:
            errors.append(f"{ref}: la respuesta correcta debe coincidir con exactamente 1 opción")
    counts = Counter(question.get("componente") for question in questions)
    for component in COMPONENT_NAMES:
        if counts[component] < QUESTIONS_PER_COMPONENT:
            errors.append(f"{component}: {counts[component]} preguntas, se requieren {QUESTIONS_PER_COMPONENT}")
    return errors


def shuffled_options(question: dict, rng: random.Random) -> list[tuple[str, bool]]:
    # En los JSON la correcta está en la posición B el 60 % de las veces; mezclar evita ese sesgo.
    options = [(option, option == question["correcta"]) for option in question["opciones"]]
    rng.shuffle(options)
    return options


def insert_question_bank(connection: Connection, questions: list[dict], rng: random.Random) -> None:
    subject_id = connection.execute(
        text("INSERT INTO materias (nombre) VALUES (:name) RETURNING id_materia"), {"name": SUBJECT_NAME}
    ).scalar_one()
    component_ids = {
        key: connection.execute(
            text("INSERT INTO componentes (id_materia, nombre) VALUES (:subject, :name) RETURNING id_componente"),
            {"subject": subject_id, "name": name},
        ).scalar_one()
        for key, name in COMPONENT_NAMES.items()
    }
    level_ids = {
        key: connection.execute(
            text("INSERT INTO niveles_dificultad (nombre) VALUES (:name) RETURNING id_nivel"), {"name": name}
        ).scalar_one()
        for key, name in LEVEL_NAMES.items()
    }
    option_rows: list[dict] = []
    for question in questions:
        question_id = connection.execute(
            text(
                "INSERT INTO preguntas (id_componente, id_nivel, enunciado) "
                "VALUES (:component, :level, :statement) RETURNING id_pregunta"
            ),
            {
                "component": component_ids[question["componente"]],
                "level": level_ids[question["nivel"]],
                "statement": question["pregunta"].strip(),
            },
        ).scalar_one()
        option_rows.extend(
            {"question": question_id, "text": option, "correct": is_correct}
            for option, is_correct in shuffled_options(question, rng)
        )
    connection.execute(
        text(
            "INSERT INTO opciones_respuesta (id_pregunta, texto_opcion, es_correcta) "
            "VALUES (:question, :text, :correct)"
        ),
        option_rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga el banco de preguntas en Neon.")
    parser.add_argument("--dry-run", action="store_true", help="Solo valida los JSON, no escribe en la BD.")
    args = parser.parse_args()

    questions = read_questions()
    errors = validate_questions(questions)
    if errors:
        print("Datos inválidos, no se cargó nada:", *errors, sep="\n  ")
        return 1
    print(f"Validación correcta: {len(questions)} preguntas.")
    if args.dry_run:
        return 0

    with engine.begin() as connection:  # una transacción: o se carga todo o nada
        # f-string seguro: los nombres salen de la constante BANK_TABLES, nunca de datos externos.
        existing = {table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in BANK_TABLES}
        if any(existing.values()):
            print("El banco ya tiene datos, no se cargó nada:", existing)
            return 1
        insert_question_bank(connection, questions, random.Random(SHUFFLE_SEED))
        loaded = {table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in BANK_TABLES}
    print("Banco cargado:", loaded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
