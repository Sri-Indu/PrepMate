import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis import AnalysisError, analyze_candidate, parse_analysis_json
from app.services.llm import LlmResult
from app.services.pdf import PdfExtractionError
from app.services.rag import RetrievedChunk
from tests.pdf_bytes import build_simple_pdf

client = TestClient(app)

VALID_JD = (
    "Software Engineer role requiring Java, SQL, REST APIs, data structures, "
    "and introductory system design. Nice to have: operating systems."
)

MOCK_ANALYSIS = {
    "summary": "Java and SQL match the role; system design needs practice.",
    "strengths": ["Java", "SQL", "React"],
    "skill_gaps": ["System Design", "Operating Systems"],
    "relevant_experience": ["Internship building REST APIs and React tables"],
    "interview_topics": ["DSA", "SQL", "System Design"],
    "preparation_plan": ["Review OS processes", "Practice two system-design sketches"],
}


class FakeRagStore:
    size = 2

    def add_document(self, text: str, source: str, **kwargs: object) -> int:
        assert text
        assert source in {"resume", "job_description"}
        return 1

    def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(0, "resume", "Java SQL React internship REST APIs", 0.9),
            RetrievedChunk(1, "job_description", "Requires system design and OS", 0.8),
        ]


def fake_generate(prompt: str, *, system: str | None = None) -> LlmResult:
    assert "Retrieved excerpts" in prompt
    assert system
    return LlmResult(model="gemma2:2b", text=json.dumps(MOCK_ANALYSIS))


def test_parse_analysis_json_strips_markdown_fence() -> None:
    raw = "Here you go:\n```json\n" + json.dumps(MOCK_ANALYSIS) + "\n```\n"
    parsed = parse_analysis_json(raw)
    assert parsed["strengths"] == ["Java", "SQL", "React"]
    assert parsed["skill_gaps"][0] == "System Design"


def test_parse_analysis_json_rejects_plain_text() -> None:
    with pytest.raises(AnalysisError, match="valid JSON"):
        parse_analysis_json("sorry I cannot help")


def test_analyze_candidate_success_with_mocks() -> None:
    pdf = build_simple_pdf("Alex Rivera Java SQL React REST APIs internship")
    result = analyze_candidate(
        pdf,
        "demo_resume.pdf",
        VALID_JD,
        rag_store=FakeRagStore(),  # type: ignore[arg-type]
        generate=fake_generate,
    )
    assert result.stored is False
    assert result.model == "gemma2:2b"
    assert result.strengths == ["Java", "SQL", "React"]
    assert result.skill_gaps == ["System Design", "Operating Systems"]
    assert result.relevant_experience
    assert result.interview_topics
    assert result.preparation_plan
    assert result.summary


def test_analyze_candidate_rejects_short_job_description() -> None:
    pdf = build_simple_pdf("Alex Rivera Java SQL React")
    with pytest.raises(AnalysisError, match="Job description"):
        analyze_candidate(
            pdf,
            "demo_resume.pdf",
            "too short",
            rag_store=FakeRagStore(),  # type: ignore[arg-type]
            generate=fake_generate,
        )


def test_analyze_candidate_rejects_non_pdf() -> None:
    with pytest.raises(PdfExtractionError):
        analyze_candidate(
            b"not a pdf",
            "resume.pdf",
            VALID_JD,
            rag_store=FakeRagStore(),  # type: ignore[arg-type]
            generate=fake_generate,
        )


def test_analysis_endpoint_missing_job_description() -> None:
    pdf = build_simple_pdf("Alex Rivera Java SQL React REST APIs internship")
    response = client.post(
        "/analysis",
        files={"resume": ("demo_resume.pdf", pdf, "application/pdf")},
    )
    assert response.status_code in {400, 422}


def test_analysis_endpoint_short_job_description() -> None:
    pdf = build_simple_pdf("Alex Rivera Java SQL React REST APIs internship")
    response = client.post(
        "/analysis",
        files={"resume": ("demo_resume.pdf", pdf, "application/pdf")},
        data={"job_description": "too short"},
    )
    assert response.status_code == 400
    assert "job description" in response.json()["detail"].lower()


def test_analysis_endpoint_invalid_pdf() -> None:
    response = client.post(
        "/analysis",
        files={"resume": ("notes.txt", b"hello", "text/plain")},
        data={"job_description": VALID_JD},
    )
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()
