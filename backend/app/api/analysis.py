"""POST /analysis — resume PDF + job description → structured Gemma analysis."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.analysis import CandidateAnalysis
from app.services.analysis import AnalysisError, analyze_candidate
from app.services.llm import LlmError
from app.services.pdf import PdfExtractionError

router = APIRouter(prefix="/analysis", tags=["analysis"])

_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


@router.post("", response_model=CandidateAnalysis)
async def create_analysis(
    resume: Annotated[UploadFile, File(description="Resume PDF")],
    job_description: Annotated[str, Form(description="Target job description text")],
) -> CandidateAnalysis:
    filename = resume.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a .pdf resume.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded resume is empty.",
        )

    try:
        return analyze_candidate(data, filename, job_description)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
