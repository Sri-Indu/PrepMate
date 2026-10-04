"""Extract text from PDF bytes in memory using pypdf.

pypdf reads the PDF structure and pulls text from each page. We never write
the uploaded file to disk — callers pass bytes and we return strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfExtractionError(Exception):
    """Raised when the file is not a readable, unencrypted PDF."""


@dataclass(frozen=True)
class ExtractedPdf:
    filename: str
    page_count: int
    character_count: int
    text: str


def extract_pdf_text(data: bytes, filename: str) -> ExtractedPdf:
    if not data.startswith(b"%PDF"):
        raise PdfExtractionError("File is not a PDF (missing %PDF header).")

    try:
        reader = PdfReader(BytesIO(data), strict=False)
    except PdfReadError as exc:
        raise PdfExtractionError("Could not parse the PDF.") from exc
    except Exception as exc:  # noqa: BLE001 — pypdf can raise several types
        raise PdfExtractionError("Could not parse the PDF.") from exc

    if reader.is_encrypted:
        raise PdfExtractionError("Encrypted PDFs are not supported.")

    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    text = "\n".join(pages).strip()
    return ExtractedPdf(
        filename=filename,
        page_count=len(reader.pages),
        character_count=len(text),
        text=text,
    )
