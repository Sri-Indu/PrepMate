"""Adaptive mock interview: Gemma writes questions/evals; Python picks strategy.

Session state lives in RAM. Resume PDFs are extracted then discarded.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.models.interview import (
    AnswerEvaluation,
    InterviewReport,
    InterviewTurnResponse,
    Strategy,
)
from app.services.llm import LlmError, LlmResult, generate_text
from app.services.pdf import extract_pdf_text
from app.services.rag import InMemoryRagStore

TOTAL_QUESTIONS = 2
MIN_JOB_DESCRIPTION_CHARS = 30

DEFAULT_TOPICS = [
    "REST APIs",
    "PostgreSQL",
    "Data Structures and Algorithms",
    "Object-Oriented Programming",
    "Docker",
    "System Design",
]

_QUESTION_SYSTEM = """You are PrepMate, a technical interviewer.
Ask exactly ONE question. Use only the resume/JD excerpts.
Reply with JSON only: {"question": string, "topic": string}.
No markdown, no answer key.
"""

_EVAL_SYSTEM = """You are PrepMate, scoring one interview answer.
Use only the excerpts and the answer. Do not invent resume facts.
Reply with JSON only:
{"score":0-10,"correctness":0-10,"depth":0-10,"clarity":0-10,"completeness":0-10,
"strengths":[],"missing_concepts":[],"feedback":""}
"""


class InterviewError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


GenerateFn = Callable[..., LlmResult]


@dataclass
class InterviewSession:
    session_id: str
    rag: InMemoryRagStore
    topic: str
    strategy: Strategy
    current_question: str
    question_number: int = 1
    total_questions: int = TOTAL_QUESTIONS
    answers: list[str] = field(default_factory=list)
    evaluations: list[AnswerEvaluation] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    status: str = "in_progress"
    topic_index: int = 0


def select_strategy(evaluation: AnswerEvaluation, session: InterviewSession) -> Strategy:
    """Deterministic next-step rules. Gemma does not choose the strategy."""
    previous_missing = {
        item.strip().lower()
        for prior in session.evaluations
        for item in prior.missing_concepts
        if item.strip()
    }
    current_missing = [item.strip().lower() for item in evaluation.missing_concepts if item.strip()]

    if evaluation.correctness <= 4:
        return "reinforce_weakness"
    if current_missing and any(item in previous_missing for item in current_missing):
        return "reinforce_weakness"
    if evaluation.correctness >= 6 and evaluation.depth <= 5:
        return "follow_up"
    if evaluation.score >= 8:
        return "harder_question"
    if session.strategy == "follow_up":
        return "same_topic"
    return "new_topic"


def build_report(session: InterviewSession) -> InterviewReport:
    scores = [item.score for item in session.evaluations]
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0

    strengths: list[str] = []
    for item in session.evaluations:
        for strength in item.strengths:
            if strength not in strengths:
                strengths.append(strength)

    weaknesses: list[str] = []
    for item in session.weaknesses:
        if item not in weaknesses:
            weaknesses.append(item)
    for item in session.evaluations:
        for concept in item.missing_concepts:
            if concept not in weaknesses:
                weaknesses.append(concept)

    topics: list[str] = []
    if session.topic and any(item.score < 6 for item in session.evaluations):
        topics.append(session.topic)
    for item in weaknesses:
        if item not in topics:
            topics.append(item)

    steps = [
        f"Revise: {topics[0]}." if topics else "Review the job description required skills.",
        "Re-answer the weakest question out loud with examples from your projects.",
        "Practice one follow-up on a missing concept from this session.",
    ]
    return InterviewReport(
        overall_score=overall,
        strengths=strengths[:6],
        weaknesses=weaknesses[:6],
        topics_to_revise=topics[:6],
        recommended_next_steps=steps,
    )


def start_interview(
    resume_bytes: bytes,
    filename: str,
    job_description: str,
    *,
    sessions: dict[str, InterviewSession],
    rag_store: InMemoryRagStore | None = None,
    generate: GenerateFn | None = None,
) -> InterviewTurnResponse:
    jd = " ".join(job_description.split())
    if len(jd) < MIN_JOB_DESCRIPTION_CHARS:
        raise InterviewError(
            f"Job description must be at least {MIN_JOB_DESCRIPTION_CHARS} characters.",
            status_code=400,
        )

    extracted = extract_pdf_text(resume_bytes, filename)
    if extracted.character_count < 20:
        raise InterviewError("The PDF did not contain enough extractable text.", status_code=400)

    store = rag_store or InMemoryRagStore()
    store.add_document(extracted.text, "resume")
    store.add_document(jd, "job_description")
    if store.size == 0:
        raise InterviewError("Could not index the resume and job description.", status_code=400)

    session_id = str(uuid.uuid4())
    topic = DEFAULT_TOPICS[0]
    session = InterviewSession(
        session_id=session_id,
        rag=store,
        topic=topic,
        strategy="new_topic",
        current_question="",
        topic_index=0,
    )
    question, topic = _generate_question(session, generate=generate or generate_text)
    session.current_question = question
    session.topic = topic
    sessions[session_id] = session
    return _to_response(session)


def submit_answer(
    session_id: str,
    answer: str,
    *,
    sessions: dict[str, InterviewSession],
    generate: GenerateFn | None = None,
) -> InterviewTurnResponse:
    session = sessions.get(session_id)
    if session is None:
        raise InterviewError("Interview session not found.", status_code=404)
    if session.status == "completed":
        raise InterviewError("This interview is already finished.", status_code=400)

    cleaned = answer.strip()
    if not cleaned:
        raise InterviewError("Answer must not be empty.", status_code=400)

    generate_fn = generate or generate_text
    evaluation = _evaluate_answer(session, cleaned, generate=generate_fn)
    session.answers.append(cleaned)
    for concept in evaluation.missing_concepts:
        if concept not in session.weaknesses:
            session.weaknesses.append(concept)

    next_strategy = select_strategy(evaluation, session)
    session.evaluations.append(evaluation)

    if len(session.evaluations) >= session.total_questions:
        session.status = "completed"
        session.strategy = next_strategy
        return _to_response(session, evaluation=evaluation, report=build_report(session))

    session.strategy = next_strategy
    session.topic = _next_topic(session, evaluation)
    session.question_number += 1
    question, topic = _generate_question(session, generate=generate_fn)
    session.current_question = question
    session.topic = topic
    return _to_response(session, evaluation=evaluation)


def _next_topic(session: InterviewSession, evaluation: AnswerEvaluation) -> str:
    if session.strategy == "reinforce_weakness" and evaluation.missing_concepts:
        return evaluation.missing_concepts[0]
    if session.strategy in {"follow_up", "harder_question", "same_topic"}:
        return session.topic
    session.topic_index = (session.topic_index + 1) % len(DEFAULT_TOPICS)
    return DEFAULT_TOPICS[session.topic_index]


def _generate_question(
    session: InterviewSession,
    *,
    generate: GenerateFn,
) -> tuple[str, str]:
    context = _context(session)
    prompt = (
        f"Strategy: {session.strategy}\n"
        f"Topic: {session.topic}\n"
        f"Question number: {session.question_number} of {session.total_questions}\n"
        f"Known weaknesses: {', '.join(session.weaknesses) or 'none'}\n"
        f"Previous question: {session.current_question or 'none'}\n\n"
        f"Retrieved excerpts:\n{context}\n\n"
        "Generate the next interview question now."
    )
    try:
        result = generate(prompt, system=_QUESTION_SYSTEM)
    except LlmError:
        raise
    data = _parse_json_object(result.text)
    question = str(data.get("question") or "").strip()
    if not question:
        raise InterviewError("The model did not return a question.", status_code=502)
    topic = str(data.get("topic") or session.topic).strip() or session.topic
    return question, topic


def _evaluate_answer(
    session: InterviewSession,
    answer: str,
    *,
    generate: GenerateFn,
) -> AnswerEvaluation:
    context = _context(session)
    prompt = (
        f"Question: {session.current_question}\n"
        f"Topic: {session.topic}\n"
        f"Candidate answer:\n{answer}\n\n"
        f"Retrieved excerpts:\n{context}\n\n"
        "Score this answer now."
    )
    try:
        result = generate(prompt, system=_EVAL_SYSTEM)
    except LlmError:
        raise
    data = _parse_json_object(result.text)
    return AnswerEvaluation(
        score=_score(data.get("score")),
        correctness=_score(data.get("correctness")),
        depth=_score(data.get("depth")),
        clarity=_score(data.get("clarity")),
        completeness=_score(data.get("completeness")),
        strengths=_as_str_list(data.get("strengths")),
        missing_concepts=_as_str_list(data.get("missing_concepts")),
        feedback=str(data.get("feedback") or "").strip(),
    )


def _context(session: InterviewSession) -> str:
    query = f"{session.topic} {session.strategy} interview question resume job description"
    hits = session.rag.search(query, k=settings.rag_top_k)
    if not hits:
        return "(no retrieved excerpts)"
    return "\n\n".join(f"[{hit.source}] {hit.text}" for hit in hits[:8])


def _to_response(
    session: InterviewSession,
    *,
    evaluation: AnswerEvaluation | None = None,
    report: InterviewReport | None = None,
) -> InterviewTurnResponse:
    return InterviewTurnResponse(
        session_id=session.session_id,
        status="completed" if session.status == "completed" else "in_progress",
        question_number=session.question_number,
        total_questions=session.total_questions,
        topic=session.topic,
        strategy=session.strategy,
        question=None if session.status == "completed" else session.current_question,
        evaluation=evaluation,
        report=report,
        stored=False,
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise InterviewError("The model did not return valid JSON.", status_code=502)
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InterviewError("The model did not return valid JSON.", status_code=502) from exc
    if not isinstance(data, dict):
        raise InterviewError("The model did not return a JSON object.", status_code=502)
    return data


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _score(value: Any) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = 0
    return max(0, min(10, number))
