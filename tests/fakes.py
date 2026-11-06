from app.domain.entities import Student
from app.domain.exceptions import ConflictError


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
