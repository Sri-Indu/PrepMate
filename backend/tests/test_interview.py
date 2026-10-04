import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.interview import AnswerEvaluation
from app.services.interview import (
    InterviewError,
    InterviewSession,
    build_report,
    select_strategy,
    start_interview,
    submit_answer,
)
from app.services.llm import LlmResult
from app.services.pdf import PdfExtractionError
from app.services.rag import RetrievedChunk
from tests.pdf_bytes import build_simple_pdf

client = TestClient(app)

VALID_JD = (
    "Software Engineer role requiring Java, Spring Boot, REST APIs, PostgreSQL, "
    "Docker, DSA, OOP, and basic system design. Kafka and AWS are also used."
)


class FakeRagStore:
    size = 2

    def add_document(self, text: str, source: str, **kwargs: object) -> int:
        return 1

    def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(0, "resume", "Java REST APIs PostgreSQL internship", 0.9),
            RetrievedChunk(1, "job_description", "Requires Spring Boot Kafka AWS", 0.8),
        ]


def fake_generate(prompt: str, *, system: str | None = None) -> LlmResult:
    blob = f"{system or ''}\n{prompt}"
    if "Score this answer" in blob or "correctness" in blob:
        payload = {
            "score": 7,
            "correctness": 7,
            "depth": 4,
            "clarity": 7,
            "completeness": 5,
            "strengths": ["Clear structure"],
            "missing_concepts": ["indexes"],
            "feedback": "Mention indexing.",
        }
        if "strong answer" in prompt.lower():
            payload.update(
                {
                    "score": 9,
                    "correctness": 9,
                    "depth": 8,
                    "clarity": 8,
                    "completeness": 8,
                    "missing_concepts": [],
                    "feedback": "Strong.",
                }
            )
        return LlmResult(model="gemma2:2b", text=json.dumps(payload))
    return LlmResult(
        model="gemma2:2b",
        text=json.dumps({"question": "Explain REST idempotency.", "topic": "REST APIs"}),
    )


def _session(**kwargs: object) -> InterviewSession:
    values = {
        "session_id": "test",
        "rag": FakeRagStore(),
        "topic": "REST APIs",
        "strategy": "new_topic",
        "current_question": "What is REST?",
    }
    values.update(kwargs)
    return InterviewSession(**values)  # type: ignore[arg-type]


def test_select_strategy_low_correctness() -> None:
    evaluation = AnswerEvaluation(
        score=3, correctness=3, depth=3, clarity=5, completeness=3, missing_concepts=["Kafka"]
    )
    assert select_strategy(evaluation, _session()) == "reinforce_weakness"


def test_select_strategy_repeated_weakness() -> None:
    prior = AnswerEvaluation(
        score=5, correctness=5, depth=5, clarity=5, completeness=5, missing_concepts=["Kafka"]
    )
    evaluation = AnswerEvaluation(
        score=6, correctness=6, depth=6, clarity=6, completeness=6, missing_concepts=["Kafka"]
    )
    session = _session()
    session.evaluations.append(prior)
    assert select_strategy(evaluation, session) == "reinforce_weakness"


def test_select_strategy_shallow_follow_up() -> None:
    evaluation = AnswerEvaluation(
        score=7, correctness=7, depth=4, clarity=8, completeness=6
    )
    assert select_strategy(evaluation, _session()) == "follow_up"


def test_select_strategy_strong_harder() -> None:
    evaluation = AnswerEvaluation(
        score=9, correctness=9, depth=8, clarity=8, completeness=8
    )
    assert select_strategy(evaluation, _session()) == "harder_question"


def test_select_strategy_same_topic_after_follow_up() -> None:
    evaluation = AnswerEvaluation(
        score=6, correctness=5, depth=6, clarity=6, completeness=6
    )
    session = _session(strategy="follow_up")
    assert select_strategy(evaluation, session) == "same_topic"


def test_start_interview_returns_first_question() -> None:
    sessions: dict = {}
    pdf = build_simple_pdf("Alex Rivera Java REST APIs PostgreSQL internship Docker")
    result = start_interview(
        pdf,
        "demo_resume.pdf",
        VALID_JD,
        sessions=sessions,
        rag_store=FakeRagStore(),  # type: ignore[arg-type]
        generate=fake_generate,
    )
    assert result.status == "in_progress"
    assert result.question_number == 1
    assert result.total_questions == 2
    assert result.strategy == "new_topic"
    assert result.question
    assert result.stored is False
    assert result.session_id in sessions


def test_submit_answer_generates_follow_up_then_report() -> None:
    sessions: dict = {}
    pdf = build_simple_pdf("Alex Rivera Java REST APIs PostgreSQL internship Docker")
    start = start_interview(
        pdf,
        "demo_resume.pdf",
        VALID_JD,
        sessions=sessions,
        rag_store=FakeRagStore(),  # type: ignore[arg-type]
        generate=fake_generate,
    )
    first = submit_answer(start.session_id, "REST uses HTTP methods.", sessions=sessions, generate=fake_generate)
    assert first.status == "in_progress"
    assert first.question_number == 2
    assert first.evaluation is not None
    assert first.evaluation.score == 7
    assert first.strategy == "follow_up"
    assert first.question

    final = submit_answer(start.session_id, "I would add indexes.", sessions=sessions, generate=fake_generate)
    assert final.status == "completed"
    assert final.question is None
    assert final.report is not None
    assert final.report.overall_score == 7.0
    assert final.evaluation is not None


def test_build_report_aggregates_history() -> None:
    session = _session()
    session.evaluations = [
        AnswerEvaluation(
            score=4,
            correctness=4,
            depth=3,
            clarity=5,
            completeness=4,
            strengths=["Honest"],
            missing_concepts=["Kafka"],
        ),
        AnswerEvaluation(
            score=8,
            correctness=8,
            depth=7,
            clarity=8,
            completeness=8,
            strengths=["Examples"],
            missing_concepts=[],
        ),
    ]
    session.weaknesses = ["Kafka"]
    report = build_report(session)
    assert report.overall_score == 6.0
    assert "Honest" in report.strengths
    assert "Kafka" in report.weaknesses
    assert report.recommended_next_steps


def test_start_interview_rejects_non_pdf() -> None:
    with pytest.raises(PdfExtractionError):
        start_interview(
            b"not a pdf",
            "resume.pdf",
            VALID_JD,
            sessions={},
            rag_store=FakeRagStore(),  # type: ignore[arg-type]
            generate=fake_generate,
        )


def test_submit_answer_unknown_session() -> None:
    with pytest.raises(InterviewError, match="not found"):
        submit_answer("missing", "an answer", sessions={}, generate=fake_generate)


def test_interview_endpoint_invalid_pdf() -> None:
    response = client.post(
        "/interview/start",
        files={"resume": ("notes.txt", b"hello", "text/plain")},
        data={"job_description": VALID_JD},
    )
    assert response.status_code == 400


def test_interview_endpoint_unknown_session() -> None:
    response = client.post("/interview/nope/answer", json={"answer": "hello there"})
    assert response.status_code == 404
