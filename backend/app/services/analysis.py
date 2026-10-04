"""Candidate analysis: PDF + JD → RAG context → Gemma JSON.

Uses existing extract_pdf_text, InMemoryRagStore, and generate_text.
Does not write the resume to disk. The FAISS index lives only for this request.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.models.analysis import CandidateAnalysis
from app.services.llm import LlmError, LlmResult, generate_text
from app.services.pdf import PdfExtractionError, extract_pdf_text
from app.services.rag import InMemoryRagStore, RetrievedChunk

MIN_JOB_DESCRIPTION_CHARS = 30

_RETRIEVAL_QUERIES = (
    "candidate skills strengths programming languages frameworks tools",
    "work experience internships projects responsibilities",
    "job requirements required skills system design operating systems",
    "interview topics data structures databases networks",
)

_SYSTEM_PROMPT = """You are PrepMate, a local interview-prep assistant.
Use ONLY the resume and job-description excerpts provided.
Do not invent employers, degrees, or skills that are not in the excerpts.
Reply with a single JSON object and no markdown. Keys:
summary (string),
strengths (array of strings),
skill_gaps (array of strings),
relevant_experience (array of strings),
interview_topics (array of strings),
preparation_plan (array of short strings).
"""


class AnalysisError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


GenerateFn = Callable[..., LlmResult]


def analyze_candidate(
    resume_bytes: bytes,
    filename: str,
    job_description: str,
    *,
    rag_store: InMemoryRagStore | None = None,
    generate: GenerateFn | None = None,
) -> CandidateAnalysis:
    jd = " ".join(job_description.split())
    if len(jd) < MIN_JOB_DESCRIPTION_CHARS:
        raise AnalysisError(
            f"Job description must be at least {MIN_JOB_DESCRIPTION_CHARS} characters.",
            status_code=400,
        )

    extracted = extract_pdf_text(resume_bytes, filename)
    if extracted.character_count < 20:
        raise AnalysisError(
            "The PDF did not contain enough extractable text.",
            status_code=400,
        )

    store = rag_store or InMemoryRagStore()
    store.add_document(extracted.text, "resume")
    store.add_document(jd, "job_description")
    if store.size == 0:
        raise AnalysisError("Could not index the resume and job description.", status_code=400)

    context = _collect_context(store)
    prompt = _build_prompt(context, jd)
    generate_fn = generate or generate_text
    try:
        result = generate_fn(prompt, system=_SYSTEM_PROMPT)
    except LlmError:
        raise

    parsed = parse_analysis_json(result.text)
    return CandidateAnalysis(
        **parsed,
        model=result.model or settings.llm_model,
        stored=False,
    )


def _collect_context(store: InMemoryRagStore) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    for query in _RETRIEVAL_QUERIES:
        for hit in store.search(query, k=settings.rag_top_k):
            key = f"{hit.source}:{hit.text}"
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"[{hit.source}] {hit.text}")
            if len(parts) >= 12:
                return "\n\n".join(parts)
    return "\n\n".join(parts)


def _build_prompt(context: str, job_description: str) -> str:
    return (
        "Retrieved excerpts:\n"
        f"{context}\n\n"
        "Full job description (for requirements only):\n"
        f"{job_description[:3000]}\n\n"
        "Produce the JSON analysis now."
    )


def parse_analysis_json(raw: str) -> dict[str, Any]:
    """Pull the first JSON object out of a Gemma reply (may include extra prose)."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AnalysisError(
                "The model did not return valid JSON. Try again.",
                status_code=502,
            )
        text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(
            "The model did not return valid JSON. Try again.",
            status_code=502,
        ) from exc

    if not isinstance(data, dict):
        raise AnalysisError("The model did not return a JSON object.", status_code=502)

    return {
        "summary": str(data.get("summary") or "").strip(),
        "strengths": _as_str_list(data.get("strengths")),
        "skill_gaps": _as_str_list(data.get("skill_gaps")),
        "relevant_experience": _as_str_list(data.get("relevant_experience")),
        "interview_topics": _as_str_list(data.get("interview_topics")),
        "preparation_plan": _as_str_list(data.get("preparation_plan")),
    }


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
