from fastapi import APIRouter, Depends, status

from app.application.exams import StartExam, SubmitExam
from app.domain.entities import Student
from app.domain.exceptions import InvalidDataError
from app.presentation.dependencies import get_current_student, get_start_exam, get_submit_exam
from app.presentation.schemas import (
    ComponentScoreResponse,
    ExamQuestionResponse,
    ExamResultResponse,
    OptionResponse,
    StartExamResponse,
    SubmitExamRequest,
)

router = APIRouter(prefix="/api/v1/exams", tags=["exams"])


@router.post(
    "",
    response_model=StartExamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar un examen de 30 preguntas (10 por componente)",
)
def start_exam(
    student: Student = Depends(get_current_student),
    use_case: StartExam = Depends(get_start_exam),
) -> StartExamResponse:
    exam = use_case.execute(student.id)
    return StartExamResponse(
        exam_id=exam.id,
        started_at=exam.started_at,
        questions=[
            ExamQuestionResponse(
                question_id=question.id,
                position=position,
                component=question.component,
                difficulty=question.difficulty,
                statement=question.statement,
                options=[OptionResponse(option_id=option.id, text=option.text) for option in question.options],
            )
            for position, question in enumerate(exam.questions, start=1)
        ],
    )


@router.post("/{exam_id}/submit", response_model=ExamResultResponse, summary="Enviar respuestas y calificar")
def submit_exam(
    exam_id: int,
    body: SubmitExamRequest,
    student: Student = Depends(get_current_student),
    use_case: SubmitExam = Depends(get_submit_exam),
) -> ExamResultResponse:
    answers = {answer.question_id: answer.option_id for answer in body.answers}
    if len(answers) != len(body.answers):
        raise InvalidDataError("Hay preguntas respondidas más de una vez")
    result = use_case.execute(student.id, exam_id, answers)
    return ExamResultResponse(
        exam_id=result.exam_id,
        total_score=result.total_score,
        max_score=result.max_score,
        components=[
            ComponentScoreResponse(component=c.component, score=c.score, max_score=c.max_score)
            for c in result.components
        ],
    )
