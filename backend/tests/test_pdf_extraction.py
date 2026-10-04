from pathlib import Path

import pytest

from app.services.pdf import PdfExtractionError, extract_pdf_text
from tests.pdf_bytes import build_simple_pdf

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample"


def test_extract_text_from_generated_pdf() -> None:
    data = build_simple_pdf("DEMO DATA fictional resume Alex Rivera Java SQL")
    result = extract_pdf_text(data, "demo_resume.pdf")

    assert result.page_count == 1
    assert result.character_count > 0
    assert "Alex Rivera" in result.text
    assert "Java" in result.text
    assert result.filename == "demo_resume.pdf"


def test_extract_text_from_sample_pdf() -> None:
    pdf_path = SAMPLE_DIR / "demo_resume.pdf"
    assert pdf_path.is_file(), "sample/demo_resume.pdf should exist for this test"
    result = extract_pdf_text(pdf_path.read_bytes(), pdf_path.name)

    assert result.page_count == 1
    assert "Alex Rivera" in result.text


def test_reject_non_pdf_bytes() -> None:
    with pytest.raises(PdfExtractionError, match="not a PDF"):
        extract_pdf_text(b"this is not a pdf", "notes.txt")
