from app.domain.entities import ExamResult, ExamStatus, StartedExam
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.ports import ExamRepository, QuestionRepository
from app.domain.scoring import QUESTIONS_PER_COMPONENT, arrange_exam, grade_exam


class StartExam:
    def __init__(self, questions: QuestionRepository, exams: ExamRepository) -> None:
        self.questions = questions
        self.exams = exams

    def execute(self, student_id: int) -> StartedExam:
        selected = arrange_exam(self.questions.pick_random(QUESTIONS_PER_COMPONENT))
        return self.exams.create(student_id, selected)


class SubmitExam:
    def __init__(self, exams: ExamRepository) -> None:
        self.exams = exams

    def execute(self, student_id: int, exam_id: int, answers: dict[int, int]) -> ExamResult:
        exam = self.exams.get_for_grading(exam_id, student_id)
        if exam is None:
            raise NotFoundError("Examen no encontrado")
        if exam.status is not ExamStatus.IN_PROGRESS:
            raise ConflictError("El examen ya fue enviado")
        result = grade_exam(exam, answers)
        self.exams.save_result(result)
        return result
