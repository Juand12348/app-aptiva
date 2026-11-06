from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.auth import Login, RegisterStudent
from app.presentation.dependencies import get_login, get_register_student
from app.presentation.schemas import RegisterRequest, StudentResponse, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar estudiante",
)
def register(body: RegisterRequest, use_case: RegisterStudent = Depends(get_register_student)) -> StudentResponse:
    student = use_case.execute(body.full_name, body.email, body.password)
    return StudentResponse(id=student.id, full_name=student.full_name, email=student.email)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión (en el campo username va el correo)",
)
def login(form: OAuth2PasswordRequestForm = Depends(), use_case: Login = Depends(get_login)) -> TokenResponse:
    return TokenResponse(access_token=use_case.execute(form.username, form.password))
