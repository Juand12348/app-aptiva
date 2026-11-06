import json
from types import SimpleNamespace

import pytest

from app.domain.entities import ComponentScore, DifficultyScore, ExamResult
from app.domain.exceptions import DiagnosisUnavailableError
from app.infrastructure.gemini import GeminiDiagnosisGenerator, build_results_summary

RESULT = ExamResult(
    exam_id=12345,
    total_score=6,
    max_score=10,
    components=[ComponentScore("Geometría", 6, 10, [DifficultyScore("Fácil", 3, 3), DifficultyScore("Difícil", 3, 7)])],
    answers=[],
)


class FakeClient:
    """Imita client.models.generate_content del SDK sin red."""

    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.prompts: list[str] = []
        self.models = SimpleNamespace(generate_content=self.generate_content)
        self.text, self.error = text, error

    def generate_content(self, model: str, contents: str, config: object) -> SimpleNamespace:
        self.prompts.append(contents)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


def test_summary_sends_only_scores() -> None:
    summary = build_results_summary(RESULT)
    assert summary == {
        "total_score": 6,
        "max_score": 10,
        "components": [{"component": "Geometría", "score": 6, "max_score": 10,
                        "by_difficulty": {"Fácil": "3/3", "Difícil": "3/7"}}],
    }
    assert "12345" not in json.dumps(summary)


def test_generate_parses_structured_answer() -> None:
    payload = {"strengths": ["Fáciles"], "weaknesses": ["Difíciles"], "recommendations": ["Practica", "Repasa", "Haz"]}
    client = FakeClient(text=json.dumps(payload))
    diagnosis = GeminiDiagnosisGenerator(client, "modelo").generate(RESULT)  # type: ignore[arg-type]
    assert diagnosis.recommendations == ["Practica", "Repasa", "Haz"]
    assert "3/7" in client.prompts[0]


@pytest.mark.parametrize(
    "client",
    [
        FakeClient(text="esto no es json"),
        FakeClient(text=json.dumps({"strengths": []})),
        FakeClient(text=json.dumps({"strengths": [], "weaknesses": [], "recommendations": []})),
        FakeClient(text=None),
        FakeClient(error=TimeoutError("sin red")),
    ],
)
def test_generate_failures_raise_unavailable(client: FakeClient) -> None:
    with pytest.raises(DiagnosisUnavailableError):
        GeminiDiagnosisGenerator(client, "modelo").generate(RESULT)  # type: ignore[arg-type]
