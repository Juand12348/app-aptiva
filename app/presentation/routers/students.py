from fastapi import APIRouter, Depends

from app.application.exams import GetStudentStats, ListStudentExams
from app.domain.entities import Accuracy, Student
from app.presentation.dependencies import get_current_student, get_list_student_exams, get_student_stats
from app.presentation.routers.exams import to_component_responses
from app.presentation.schemas import (
    AccuracyResponse,
    ComponentStatsResponse,
    EvolutionPointResponse,
    ExamHistoryItemResponse,
    StudentResponse,
    StudentStatsResponse,
)

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


def to_accuracy_responses(items: list[Accuracy]) -> list[AccuracyResponse]:
    return [AccuracyResponse(label=a.label, correct=a.correct, total=a.total, accuracy=a.accuracy) for a in items]


@router.get(
    "/me/stats",
    response_model=StudentStatsResponse,
    summary="Estadísticas del estudiante: evolución, componentes, dificultad y posición en el bloque",
)
def read_my_stats(
    student: Student = Depends(get_current_student),
    use_case: GetStudentStats = Depends(get_student_stats),
) -> StudentStatsResponse:
    stats = use_case.execute(student.id)
    return StudentStatsResponse(
        exams_count=stats.exams_count,
        evolution=[
            EvolutionPointResponse(
                exam_id=p.exam_id,
                finished_at=p.finished_at,
                total_score=p.total_score,
                max_score=p.max_score,
                component_scores=p.component_scores,
            )
            for p in stats.evolution
        ],
        components=[
            ComponentStatsResponse(
                component=c.component,
                average_score=c.average_score,
                latest_score=c.latest_score,
                max_score=c.max_score,
                by_difficulty=to_accuracy_responses(c.by_difficulty),
            )
            for c in stats.components
        ],
        by_difficulty=to_accuracy_responses(stats.by_difficulty),
        by_position_in_block=to_accuracy_responses(stats.by_position_in_block),
    )
