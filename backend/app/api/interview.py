"""Adaptive interview HTTP API. Sessions stay in memory."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.interview import AnswerRequest, InterviewTurnResponse
from app.services.interview import InterviewError, start_interview, submit_answer
from app.services.llm import LlmError
from app.services.pdf import PdfExtractionError
from app.store.memory import interview_sessions

router = APIRouter(prefix="/interview", tags=["interview"])

_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


@router.post("/start", response_model=InterviewTurnResponse)
async def start(
    resume: Annotated[UploadFile, File(description="Resume PDF")],
    job_description: Annotated[str, Form()],
) -> InterviewTurnResponse:
    filename = resume.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a .pdf resume.")

    content_type = (resume.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {content_type}. Use application/pdf.",
        )

    data = await resume.read(settings.max_upload_bytes + 1)
    await resume.close()

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded resume is empty.")

    try:
        return start_interview(
            data,
            filename,
            job_description,
            sessions=interview_sessions,
        )
    except PdfExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InterviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{session_id}/answer", response_model=InterviewTurnResponse)
def answer(session_id: str, body: AnswerRequest) -> InterviewTurnResponse:
    try:
        return submit_answer(session_id, body.answer, sessions=interview_sessions)
    except InterviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
