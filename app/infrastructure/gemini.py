import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.domain.entities import Diagnosis, ExamResult
from app.domain.exceptions import DiagnosisUnavailableError

PROMPT = """Eres un tutor de matemáticas. Analiza los resultados de una evaluación diagnóstica de 30 preguntas
(10 por componente) y escribe un diagnóstico para el estudiante, en español y tuteándolo.

Reglas:
- Básate SOLO en los datos entregados. No inventes temas, preguntas ni cifras que no estén en ellos.
- "strengths": de 0 a 4 fortalezas concretas (componentes o niveles de dificultad con buen desempeño).
  Si no hay ninguna, devuelve la lista vacía.
- "weaknesses": de 0 a 4 debilidades concretas. Si el desempeño es perfecto, devuelve la lista vacía.
- "recommendations": de 3 a 5 recomendaciones de estudio accionables y priorizadas, ligadas a las debilidades.
- Cada elemento es una sola oración breve, sin saltos de línea ni viñetas.

Resultados (JSON):
{results}
"""


class DiagnosisPayload(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


def build_results_summary(result: ExamResult) -> dict[str, Any]:
    """Solo puntajes: nunca datos del estudiante ni ids."""
    return {
        "total_score": result.total_score,
        "max_score": result.max_score,
        "components": [
            {
                "component": component.component,
                "score": component.score,
                "max_score": component.max_score,
                "by_difficulty": {level.difficulty: f"{level.correct}/{level.total}" for level in component.by_difficulty},
            }
            for component in result.components
        ],
    }


class GeminiDiagnosisGenerator:
    def __init__(self, client: genai.Client, model: str) -> None:
        self.client = client
        self.model = model

    def generate(self, result: ExamResult) -> Diagnosis:
        prompt = PROMPT.format(results=json.dumps(build_results_summary(result), ensure_ascii=False, indent=2))
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DiagnosisPayload,
                    temperature=0.4,
                ),
            )
            payload = DiagnosisPayload.model_validate_json(response.text or "")
        except ValidationError as error:
            raise DiagnosisUnavailableError("Gemini respondió un formato inválido") from error
        except Exception as error:  # errores de red, cuota, timeout o de la API: todos significan "sin diagnóstico"
            raise DiagnosisUnavailableError("No se pudo contactar a Gemini") from error
        if not payload.recommendations:
            raise DiagnosisUnavailableError("Gemini no devolvió recomendaciones")
        return Diagnosis(payload.strengths, payload.weaknesses, payload.recommendations)


def create_gemini_client(api_key: str, timeout_seconds: int) -> genai.Client:
    # El SDK reintenta 5 veces por defecto: con 20 s por intento el estudiante podría esperar más de un minuto.
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_seconds * 1000, retry_options=types.HttpRetryOptions(attempts=2)),
    )
