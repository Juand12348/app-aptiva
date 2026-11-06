from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import Student
from app.domain.exceptions import ConflictError
from app.infrastructure.models import Estudiante


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
