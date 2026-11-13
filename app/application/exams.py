from dataclasses import replace
from datetime import timedelta

from app.application.diagnosis import GenerateDiagnosis
from app.domain.entities import ExamHistoryItem, ExamStatus, StartedExam, StudentStats, SubmittedExam
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.ports import DiagnosisRepository, ExamRepository, QuestionRepository
from app.domain.scoring import QUESTIONS_PER_COMPONENT, arrange_exam, grade_exam
from app.domain.stats import build_stats


class StartExam:
    def __init__(self, questions: QuestionRepository, exams: ExamRepository, time_limit: timedelta) -> None:
        self.questions = questions
        self.exams = exams
        self.time_limit = time_limit

    def execute(self, student_id: int) -> StartedExam:
        selected = arrange_exam(self.questions.pick_random(QUESTIONS_PER_COMPONENT))
        exam = self.exams.create(student_id, selected)
        # Política: el envío tardío se califica igual; el límite solo lo informa al cliente.
        return replace(exam, expires_at=exam.started_at + self.time_limit)


class SubmitExam:
    def __init__(self, exams: ExamRepository, diagnosis: GenerateDiagnosis) -> None:
        self.exams = exams
        self.diagnosis = diagnosis

    def execute(self, student_id: int, exam_id: int, answers: dict[int, int]) -> SubmittedExam:
        exam = self.exams.get_for_grading(exam_id, student_id)
        if exam is None:
            raise NotFoundError("Examen no encontrado")
        if exam.status is not ExamStatus.IN_PROGRESS:
            raise ConflictError("El examen ya fue enviado")
        result = grade_exam(exam, answers)
        self.exams.save_result(result)
        return SubmittedExam(result, self.diagnosis.try_for_result(result))


class GetExamResult:
    def __init__(self, exams: ExamRepository, diagnoses: DiagnosisRepository) -> None:
        self.exams = exams
        self.diagnoses = diagnoses

    def execute(self, student_id: int, exam_id: int) -> SubmittedExam:
        status = self.exams.get_status(exam_id, student_id)
        if status is None:
            raise NotFoundError("Examen no encontrado")
        if status is not ExamStatus.FINISHED:
            raise ConflictError("El examen aún no ha sido enviado")
        return SubmittedExam(self.exams.get_result(exam_id), self.diagnoses.get(exam_id))


class ListStudentExams:
    def __init__(self, exams: ExamRepository) -> None:
        self.exams = exams

    def execute(self, student_id: int) -> list[ExamHistoryItem]:
        return self.exams.list_finished(student_id)


class GetStudentStats:
    def __init__(self, exams: ExamRepository) -> None:
        self.exams = exams

    def execute(self, student_id: int) -> StudentStats:
        return build_stats(self.exams.list_finished(student_id))
