import logging

from app.domain.entities import Diagnosis, ExamResult, ExamStatus
from app.domain.exceptions import ConflictError, DiagnosisUnavailableError, NotFoundError
from app.domain.ports import DiagnosisGenerator, DiagnosisRepository, ExamRepository

logger = logging.getLogger(__name__)


class GenerateDiagnosis:
    def __init__(self, generator: DiagnosisGenerator, diagnoses: DiagnosisRepository) -> None:
        self.generator = generator
        self.diagnoses = diagnoses

    def try_for_result(self, result: ExamResult) -> Diagnosis | None:
        """Nunca hace fallar al llamador: si la IA falla devuelve None y el examen conserva sus puntajes."""
        try:
            return self.for_result(result)
        except DiagnosisUnavailableError:
            logger.exception("No se pudo generar el diagnóstico del examen %s", result.exam_id)
            return None

    def for_result(self, result: ExamResult) -> Diagnosis:
        diagnosis = self.generator.generate(result)
        self.diagnoses.save(result.exam_id, diagnosis)
        return diagnosis


class RegenerateDiagnosis:
    def __init__(self, exams: ExamRepository, generate: GenerateDiagnosis) -> None:
        self.exams = exams
        self.generate = generate

    def execute(self, student_id: int, exam_id: int) -> Diagnosis:
        status = self.exams.get_status(exam_id, student_id)
        if status is None:
            raise NotFoundError("Examen no encontrado")
        if status is not ExamStatus.FINISHED:
            raise ConflictError("El examen aún no ha sido enviado")
        return self.generate.for_result(self.exams.get_result(exam_id))
