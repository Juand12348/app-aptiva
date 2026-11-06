import random
from collections import defaultdict
from datetime import UTC, datetime

from app.domain.entities import (
    ExamResult,
    ExamStatus,
    ExamToGrade,
    GradableQuestion,
    Option,
    Question,
    StartedExam,
    Student,
)
from app.domain.exceptions import ConflictError

COMPONENTS = ["Estadística", "Geometría", "Cálculo y Álgebra"]


class InMemoryStudentRepository:
    def __init__(self) -> None:
        self.students: dict[int, Student] = {}

    def get_by_id(self, student_id: int) -> Student | None:
        return self.students.get(student_id)

    def get_by_email(self, email: str) -> Student | None:
        return next((s for s in self.students.values() if s.email == email), None)

    def add(self, full_name: str, email: str, password_hash: str) -> Student:
        if self.get_by_email(email):
            raise ConflictError("Ya existe una cuenta con ese correo")
        student = Student(len(self.students) + 1, full_name, email, password_hash)
        self.students[student.id] = student
        return student


def make_bank(per_component: int = 12) -> tuple[list[Question], dict[int, int]]:
    """Banco falso: pregunta N tiene opciones N*10+0..3 y la correcta es N*10+2."""
    questions: list[Question] = []
    correct: dict[int, int] = {}
    for index, component in enumerate(COMPONENTS):
        for n in range(per_component):
            question_id = index * 100 + n + 1
            options = tuple(Option(question_id * 10 + k, f"Opción {k}") for k in range(4))
            questions.append(Question(question_id, index + 1, component, "Fácil", f"Pregunta {question_id}", options))
            correct[question_id] = question_id * 10 + 2
    return questions, correct


class FakeQuestionRepository:
    def __init__(self, questions: list[Question]) -> None:
        self.questions = questions

    def pick_random(self, per_component: int) -> list[Question]:
        by_component: dict[str, list[Question]] = defaultdict(list)
        for question in self.questions:
            by_component[question.component].append(question)
        return [q for group in by_component.values() for q in random.sample(group, min(per_component, len(group)))]


class InMemoryExamRepository:
    def __init__(self, correct: dict[int, int]) -> None:
        self.correct = correct
        self.exams: dict[int, dict] = {}

    def create(self, student_id: int, questions: list[Question]) -> StartedExam:
        exam_id = len(self.exams) + 1
        self.exams[exam_id] = {"student_id": student_id, "status": ExamStatus.IN_PROGRESS, "questions": questions}
        return StartedExam(exam_id, datetime.now(UTC), questions)

    def get_for_grading(self, exam_id: int, student_id: int) -> ExamToGrade | None:
        exam = self.exams.get(exam_id)
        if exam is None or exam["student_id"] != student_id:
            return None
        return ExamToGrade(
            exam_id,
            exam["status"],
            [
                GradableQuestion(q.id, q.component, frozenset(o.id for o in q.options), self.correct[q.id])
                for q in exam["questions"]
            ],
        )

    def save_result(self, result: ExamResult) -> None:
        self.exams[result.exam_id]["status"] = ExamStatus.FINISHED
        self.exams[result.exam_id]["result"] = result
