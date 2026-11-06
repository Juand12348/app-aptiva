"""Único punto donde la presentación se conecta con la infraestructura."""

from functools import lru_cache

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.application.auth import GetCurrentStudent, Login, RegisterStudent
from app.application.diagnosis import GenerateDiagnosis, RegenerateDiagnosis
from app.application.exams import GetExamResult, ListStudentExams, StartExam, SubmitExam
from app.domain.entities import Student
from app.domain.exceptions import AuthenticationError
from app.domain.ports import (
    DiagnosisGenerator,
    DiagnosisRepository,
    ExamRepository,
    QuestionRepository,
    StudentRepository,
    TokenService,
)
from app.infrastructure.config import get_settings
from app.infrastructure.database import get_session, is_database_reachable
from app.infrastructure.gemini import GeminiDiagnosisGenerator, create_gemini_client
from app.infrastructure.repositories import (
    SqlDiagnosisRepository,
    SqlExamRepository,
    SqlQuestionRepository,
    SqlStudentRepository,
)
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService

__all__ = [
    "get_current_student",
    "get_get_exam_result",
    "get_list_student_exams",
    "get_login",
    "get_regenerate_diagnosis",
    "get_register_student",
    "get_start_exam",
    "get_submit_exam",
    "is_database_reachable",
]

password_hasher = Argon2PasswordHasher()
# auto_error=False: el 401 sale de nuestro manejador, con mensaje en español.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_student_repository(session: Session = Depends(get_session)) -> StudentRepository:
    return SqlStudentRepository(session)


def get_question_repository(session: Session = Depends(get_session)) -> QuestionRepository:
    return SqlQuestionRepository(session)


def get_exam_repository(session: Session = Depends(get_session)) -> ExamRepository:
    return SqlExamRepository(session)


def get_diagnosis_repository(session: Session = Depends(get_session)) -> DiagnosisRepository:
    return SqlDiagnosisRepository(session)


@lru_cache
def get_diagnosis_generator() -> DiagnosisGenerator:
    settings = get_settings()
    client = create_gemini_client(settings.gemini_api_key, settings.gemini_timeout_seconds)
    return GeminiDiagnosisGenerator(client, settings.gemini_model)


def get_generate_diagnosis(
    generator: DiagnosisGenerator = Depends(get_diagnosis_generator),
    diagnoses: DiagnosisRepository = Depends(get_diagnosis_repository),
) -> GenerateDiagnosis:
    return GenerateDiagnosis(generator, diagnoses)


def get_start_exam(
    questions: QuestionRepository = Depends(get_question_repository),
    exams: ExamRepository = Depends(get_exam_repository),
) -> StartExam:
    return StartExam(questions, exams)


def get_submit_exam(
    exams: ExamRepository = Depends(get_exam_repository),
    diagnosis: GenerateDiagnosis = Depends(get_generate_diagnosis),
) -> SubmitExam:
    return SubmitExam(exams, diagnosis)


def get_get_exam_result(
    exams: ExamRepository = Depends(get_exam_repository),
    diagnoses: DiagnosisRepository = Depends(get_diagnosis_repository),
) -> GetExamResult:
    return GetExamResult(exams, diagnoses)


def get_list_student_exams(exams: ExamRepository = Depends(get_exam_repository)) -> ListStudentExams:
    return ListStudentExams(exams)


def get_regenerate_diagnosis(
    exams: ExamRepository = Depends(get_exam_repository),
    diagnosis: GenerateDiagnosis = Depends(get_generate_diagnosis),
) -> RegenerateDiagnosis:
    return RegenerateDiagnosis(exams, diagnosis)


def get_token_service() -> TokenService:
    settings = get_settings()
    return JwtTokenService(settings.jwt_secret_key, settings.access_token_expire_minutes)


def get_register_student(students: StudentRepository = Depends(get_student_repository)) -> RegisterStudent:
    return RegisterStudent(students, password_hasher)


def get_login(
    students: StudentRepository = Depends(get_student_repository),
    tokens: TokenService = Depends(get_token_service),
) -> Login:
    return Login(students, password_hasher, tokens)


def get_current_student(
    token: str | None = Depends(oauth2_scheme),
    students: StudentRepository = Depends(get_student_repository),
    tokens: TokenService = Depends(get_token_service),
) -> Student:
    if token is None:
        raise AuthenticationError("No autenticado")
    return GetCurrentStudent(students, tokens).execute(token)
