from app.domain.entities import Student
from app.domain.exceptions import AuthenticationError
from app.domain.ports import PasswordHasher, StudentRepository, TokenService

INVALID_CREDENTIALS = "Correo o contraseña incorrectos"


def normalize_email(email: str) -> str:
    return email.strip().lower()


class RegisterStudent:
    def __init__(self, students: StudentRepository, hasher: PasswordHasher) -> None:
        self.students = students
        self.hasher = hasher

    def execute(self, full_name: str, email: str, password: str) -> Student:
        return self.students.add(full_name.strip(), normalize_email(email), self.hasher.hash(password))


class Login:
    def __init__(self, students: StudentRepository, hasher: PasswordHasher, tokens: TokenService) -> None:
        self.students = students
        self.hasher = hasher
        self.tokens = tokens

    def execute(self, email: str, password: str) -> str:
        student = self.students.get_by_email(normalize_email(email))
        if student is None or not self.hasher.verify(password, student.password_hash):
            raise AuthenticationError(INVALID_CREDENTIALS)
        return self.tokens.create(student.id)


class GetCurrentStudent:
    def __init__(self, students: StudentRepository, tokens: TokenService) -> None:
        self.students = students
        self.tokens = tokens

    def execute(self, token: str) -> Student:
        student = self.students.get_by_id(self.tokens.read_student_id(token))
        if student is None:
            raise AuthenticationError("Token inválido o vencido")
        return student
