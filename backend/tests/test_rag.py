from pathlib import Path

import pytest

from app.services.embeddings import LocalEmbedder
from app.services.rag import InMemoryRagStore

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample"


@pytest.fixture(scope="module")
def rag_store() -> InMemoryRagStore:
    resume = (SAMPLE_DIR / "resume.txt").read_text(encoding="utf-8")
    jd = (SAMPLE_DIR / "job_description.txt").read_text(encoding="utf-8")
    store = InMemoryRagStore(LocalEmbedder())
    store.add_document(resume, "resume", chunk_size=280, overlap=40)
    store.add_document(jd, "job_description", chunk_size=280, overlap=40)
    assert store.size >= 2
    return store


def test_react_query_retrieves_resume_chunk(rag_store: InMemoryRagStore) -> None:
    hits = rag_store.search("What frontend or React experience does the candidate have?", k=3)
    assert hits
    assert any(hit.source == "resume" for hit in hits)
    combined = " ".join(hit.text.lower() for hit in hits)
    assert "react" in combined


def test_system_design_query_retrieves_job_description(
    rag_store: InMemoryRagStore,
) -> None:
    hits = rag_store.search(
        "Harborline Apps Software Engineer Spring Boot Kafka AWS job requirements",
        k=3,
    )
    assert hits
    assert any(hit.source == "job_description" for hit in hits)
    combined = " ".join(hit.text.lower() for hit in hits)
    assert "spring boot" in combined or "kafka" in combined or "harborline" in combined


def test_empty_query_returns_nothing(rag_store: InMemoryRagStore) -> None:
    assert rag_store.search("   ") == []
