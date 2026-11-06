from collections import defaultdict

from sqlalchemy import and_, bindparam, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sqlalchemy.dialects.postgresql import insert

from app.domain.entities import (
    Diagnosis,
    ExamResult,
    ExamStatus,
    ExamToGrade,
    GradableQuestion,
    GradedAnswer,
    Option,
    Question,
    StartedExam,
    Student,
)
from app.domain.exceptions import ConflictError
from app.domain.scoring import summarize
from app.infrastructure.models import (
    Componente,
    DetalleIntento,
    DiagnosticoIA,
    Estudiante,
    IntentoExamen,
    NivelDificultad,
    OpcionRespuesta,
    Pregunta,
)

# Valores reales del CHECK chk_estado_intento.
DB_STATUS = {ExamStatus.IN_PROGRESS: "En progreso", ExamStatus.FINISHED: "Finalizado"}
STATUS_FROM_DB = {value: key for key, value in DB_STATUS.items()}


def to_student(row: Estudiante) -> Student:
    return Student(id=row.id_estudiante, full_name=row.nombre, email=row.correo, password_hash=row.contrasena_hash)


class SqlStudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, student_id: int) -> Student | None:
        row = self.session.get(Estudiante, student_id)
        return to_student(row) if row else None

    def get_by_email(self, email: str) -> Student | None:
        row = self.session.scalar(select(Estudiante).where(Estudiante.correo == email))
        return to_student(row) if row else None

    def add(self, full_name: str, email: str, password_hash: str) -> Student:
        row = Estudiante(nombre=full_name, correo=email, contrasena_hash=password_hash)
        self.session.add(row)
        try:
            self.session.flush()  # obtiene el id y detecta el correo duplicado aquí, no en el commit
        except IntegrityError as error:
            # El UNIQUE de la BD cubre también el caso de dos registros simultáneos con el mismo correo.
            raise ConflictError("Ya existe una cuenta con ese correo") from error
        return to_student(row)


class SqlQuestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def pick_random(self, per_component: int) -> list[Question]:
        ranked = (
            select(
                Pregunta.id_pregunta,
                Pregunta.id_componente,
                Componente.nombre.label("component"),
                NivelDificultad.nombre.label("difficulty"),
                Pregunta.enunciado,
                func.row_number()
                .over(partition_by=Pregunta.id_componente, order_by=func.random())
                .label("rank"),
            )
            .join(Componente, Componente.id_componente == Pregunta.id_componente)
            .join(NivelDificultad, NivelDificultad.id_nivel == Pregunta.id_nivel)
            .where(Pregunta.activa)
            .subquery()
        )
        rows = self.session.execute(
            select(ranked).where(ranked.c.rank <= per_component).order_by(ranked.c.id_componente, ranked.c.rank)
        ).all()

        options: dict[int, list[Option]] = defaultdict(list)
        option_rows = self.session.execute(
            select(OpcionRespuesta.id_pregunta, OpcionRespuesta.id_opcion, OpcionRespuesta.texto_opcion)
            .where(OpcionRespuesta.id_pregunta.in_([row.id_pregunta for row in rows]))
            .order_by(OpcionRespuesta.id_opcion)
        )
        for question_id, option_id, option_text in option_rows:
            options[question_id].append(Option(option_id, option_text))

        return [
            Question(
                id=row.id_pregunta,
                component_id=row.id_componente,
                component=row.component,
                difficulty=row.difficulty,
                statement=row.enunciado,
                options=tuple(options[row.id_pregunta]),
            )
            for row in rows
        ]


class SqlExamRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, student_id: int, questions: list[Question]) -> StartedExam:
        attempt = IntentoExamen(id_estudiante=student_id, estado=DB_STATUS[ExamStatus.IN_PROGRESS])
        self.session.add(attempt)
        self.session.flush()  # id_intento y fecha_inicio vienen de la BD
        self.session.add_all(
            DetalleIntento(
                id_intento=attempt.id_intento,
                id_pregunta=question.id,
                id_componente=question.component_id,
                orden=position,
            )
            for position, question in enumerate(questions, start=1)
        )
        self.session.flush()
        return StartedExam(id=attempt.id_intento, started_at=attempt.fecha_inicio, questions=questions)

    def get_for_grading(self, exam_id: int, student_id: int) -> ExamToGrade | None:
        # FOR UPDATE: un segundo envío simultáneo espera aquí y luego ve el examen ya finalizado.
        status = self.session.scalar(
            select(IntentoExamen.estado)
            .where(IntentoExamen.id_intento == exam_id, IntentoExamen.id_estudiante == student_id)
            .with_for_update()
        )
        if status is None:
            return None

        rows = self.session.execute(
            select(
                DetalleIntento.id_pregunta,
                Componente.nombre,
                NivelDificultad.nombre,
                OpcionRespuesta.id_opcion,
                OpcionRespuesta.es_correcta,
            )
            .join(Componente, Componente.id_componente == DetalleIntento.id_componente)
            .join(Pregunta, Pregunta.id_pregunta == DetalleIntento.id_pregunta)
            .join(NivelDificultad, NivelDificultad.id_nivel == Pregunta.id_nivel)
            .join(OpcionRespuesta, OpcionRespuesta.id_pregunta == DetalleIntento.id_pregunta)
            .where(DetalleIntento.id_intento == exam_id)
            .order_by(DetalleIntento.orden, OpcionRespuesta.id_opcion)
        )
        labels: dict[int, tuple[str, str]] = {}
        option_ids: dict[int, set[int]] = defaultdict(set)
        correct: dict[int, int] = {}
        for question_id, component, difficulty, option_id, is_correct in rows:
            labels[question_id] = (component, difficulty)
            option_ids[question_id].add(option_id)
            if is_correct:
                correct[question_id] = option_id

        return ExamToGrade(
            id=exam_id,
            status=STATUS_FROM_DB[status],
            questions=[
                GradableQuestion(question_id, component, difficulty, frozenset(option_ids[question_id]), correct[question_id])
                for question_id, (component, difficulty) in labels.items()  # dict conserva el orden de `orden`
            ],
        )

    def get_status(self, exam_id: int, student_id: int) -> ExamStatus | None:
        status = self.session.scalar(
            select(IntentoExamen.estado).where(
                IntentoExamen.id_intento == exam_id, IntentoExamen.id_estudiante == student_id
            )
        )
        return STATUS_FROM_DB[status] if status else None

    def get_result(self, exam_id: int) -> ExamResult:
        rows = self.session.execute(
            select(
                DetalleIntento.id_pregunta,
                DetalleIntento.id_opcion_seleccionada,
                DetalleIntento.es_correcta,
                Componente.nombre,
                NivelDificultad.nombre,
            )
            .join(Componente, Componente.id_componente == DetalleIntento.id_componente)
            .join(Pregunta, Pregunta.id_pregunta == DetalleIntento.id_pregunta)
            .join(NivelDificultad, NivelDificultad.id_nivel == Pregunta.id_nivel)
            .where(DetalleIntento.id_intento == exam_id)
            .order_by(DetalleIntento.orden)
        ).all()
        return summarize(
            exam_id,
            [(component, difficulty) for *_, component, difficulty in rows],
            [GradedAnswer(question_id, selected, bool(correct)) for question_id, selected, correct, *_ in rows],
        )

    def save_result(self, result: ExamResult) -> None:
        detail = DetalleIntento.__table__
        # Un solo executemany para las 30 respuestas, en lugar de 30 viajes a Neon.
        self.session.execute(
            update(detail)
            .where(and_(detail.c.id_intento == bindparam("exam"), detail.c.id_pregunta == bindparam("question")))
            .values(id_opcion_seleccionada=bindparam("option"), es_correcta=bindparam("correct")),
            [
                {
                    "exam": result.exam_id,
                    "question": answer.question_id,
                    "option": answer.selected_option_id,
                    "correct": answer.is_correct,
                }
                for answer in result.answers
            ],
        )
        self.session.execute(
            update(IntentoExamen)
            .where(IntentoExamen.id_intento == result.exam_id)
            .values(
                estado=DB_STATUS[ExamStatus.FINISHED],
                fecha_fin=func.now(),
                puntaje_total=result.total_score,
            )
        )


def join_lines(items: list[str]) -> str:
    # diagnosticos_ia guarda TEXT: un elemento por línea, así que un elemento no puede contener saltos de línea.
    return "\n".join(" ".join(item.split()) for item in items if item.strip())


class SqlDiagnosisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, exam_id: int, diagnosis: Diagnosis) -> None:
        values = {
            "fortalezas": join_lines(diagnosis.strengths),
            "debilidades": join_lines(diagnosis.weaknesses),
            "recomendaciones": join_lines(diagnosis.recommendations),
        }
        statement = insert(DiagnosticoIA).values(id_intento=exam_id, **values)
        # Regenerar reemplaza el diagnóstico existente (id_intento es UNIQUE).
        self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[DiagnosticoIA.id_intento],
                set_={**values, "fecha_generacion": func.now()},
            )
        )
