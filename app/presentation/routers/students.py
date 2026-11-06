from fastapi import APIRouter, Depends

from app.application.exams import ListStudentExams
from app.domain.entities import Student
from app.presentation.dependencies import get_current_student, get_list_student_exams
from app.presentation.routers.exams import to_component_responses
from app.presentation.schemas import ExamHistoryItemResponse, StudentResponse

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("/me", response_model=StudentResponse, summary="Datos del estudiante autenticado")
def read_me(student: Student = Depends(get_current_student)) -> StudentResponse:
    return StudentResponse(id=student.id, full_name=student.full_name, email=student.email)


@router.get(
    "/me/exams",
    response_model=list[ExamHistoryItemResponse],
    summary="Historial de exámenes enviados (más reciente primero)",
)
def list_my_exams(
    student: Student = Depends(get_current_student),
    use_case: ListStudentExams = Depends(get_list_student_exams),
) -> list[ExamHistoryItemResponse]:
    return [
        ExamHistoryItemResponse(
            exam_id=item.result.exam_id,
            started_at=item.started_at,
            finished_at=item.finished_at,
            total_score=item.result.total_score,
            max_score=item.result.max_score,
            components=to_component_responses(item.result),
            has_diagnosis=item.has_diagnosis,
        )
        for item in use_case.execute(student.id)
    ]
