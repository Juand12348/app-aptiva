from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150, examples=["Ana Pérez"])
    # Validación de formato básica sin agregar la dependencia email-validator.
    email: str = Field(max_length=150, pattern=r"^\s*[^@\s]+@[^@\s]+\.[^@\s]+\s*$", examples=["ana@correo.com"])
    password: str = Field(min_length=8, max_length=128)


class StudentResponse(BaseModel):
    id: int
    full_name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class OptionResponse(BaseModel):
    option_id: int
    text: str


class ExamQuestionResponse(BaseModel):
    """Sin campo de respuesta correcta: este schema es el que ve el estudiante."""

    question_id: int
    position: int
    component: str
    difficulty: str
    statement: str
    options: list[OptionResponse]


class StartExamResponse(BaseModel):
    exam_id: int
    started_at: datetime
    questions: list[ExamQuestionResponse]


class AnswerRequest(BaseModel):
    question_id: int
    option_id: int


class SubmitExamRequest(BaseModel):
    # Las preguntas sin responder simplemente no se envían (cuentan como incorrectas).
    answers: list[AnswerRequest] = Field(max_length=30)


class DifficultyScoreResponse(BaseModel):
    difficulty: str
    correct: int
    total: int


class ComponentScoreResponse(BaseModel):
    component: str
    score: int
    max_score: int
    by_difficulty: list[DifficultyScoreResponse]


class DiagnosisResponse(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class ExamResultResponse(BaseModel):
    exam_id: int
    total_score: int
    max_score: int
    components: list[ComponentScoreResponse]
    diagnosis: DiagnosisResponse | None = Field(
        description="null si Gemini no respondió; se puede regenerar con POST /exams/{exam_id}/diagnosis"
    )
