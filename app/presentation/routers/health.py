from fastapi import APIRouter, Depends, Response, status

from app.presentation.dependencies import is_database_reachable
from app.presentation.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Estado del servidor y de la base de datos")
def check_health(response: Response, database_ok: bool = Depends(is_database_reachable)) -> HealthResponse:
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="unavailable")
    return HealthResponse(status="ok", database="ok")
