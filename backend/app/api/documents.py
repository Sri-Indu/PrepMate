"""PDF upload endpoints. Files are read into memory and then discarded."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.documents import DocumentExtractResponse, DocumentType
from app.services.pdf import PdfExtractionError, extract_pdf_text

router = APIRouter(prefix="/documents", tags=["documents"])

_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


def _looks_like_pdf_filename(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


@router.post("/extract", response_model=DocumentExtractResponse)
async def extract_document(
    file: Annotated[UploadFile, File(description="Resume or job-description PDF")],
    document_type: Annotated[
        DocumentType,
        Form(description="What this PDF represents"),
    ] = "resume",
) -> DocumentExtractResponse:
    filename = file.filename or ""
    if not filename or not _looks_like_pdf_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a .pdf file.",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {content_type}. Use application/pdf.",
        )

    data = await file.read(settings.max_upload_bytes + 1)
    # Drop any file handle / temp spool; we only keep `data` in memory.
    await file.close()

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    try:
        extracted = extract_pdf_text(data, filename)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return DocumentExtractResponse(
        document_type=document_type,
        filename=extracted.filename,
        page_count=extracted.page_count,
        character_count=extracted.character_count,
        text=extracted.text,
        stored=False,
    )
