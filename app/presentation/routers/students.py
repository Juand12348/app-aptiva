from fastapi import APIRouter, Depends

from app.domain.entities import Student
from app.presentation.dependencies import get_current_student
from app.presentation.schemas import StudentResponse

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("/me", response_model=StudentResponse, summary="Datos del estudiante autenticado")
def read_me(student: Student = Depends(get_current_student)) -> StudentResponse:
    return StudentResponse(id=student.id, full_name=student.full_name, email=student.email)
