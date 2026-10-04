"""Index resume/JD text and retrieve relevant chunks. In-memory only."""

from fastapi import APIRouter, HTTPException, status

from app.models.rag import (
    RagHit,
    RagIndexRequest,
    RagIndexResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from app.store.memory import rag_store

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/index", response_model=RagIndexResponse)
def index_documents(body: RagIndexRequest) -> RagIndexResponse:
    rag_store.clear()
    resume_chunks = rag_store.add_document(body.resume_text, "resume")
    jd_chunks = rag_store.add_document(body.job_description_text, "job_description")
    if rag_store.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text chunks were produced from the documents.",
        )
    return RagIndexResponse(
        resume_chunks=resume_chunks,
        job_description_chunks=jd_chunks,
        total_chunks=rag_store.size,
        persisted=False,
    )


@router.post("/query", response_model=RagQueryResponse)
def query_index(body: RagQueryRequest) -> RagQueryResponse:
    if rag_store.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index is empty. POST /rag/index first.",
        )
    hits = rag_store.search(body.query, k=body.k)
    return RagQueryResponse(
        query=body.query,
        hits=[
            RagHit(
                chunk_id=hit.chunk_id,
                source=hit.source,
                text=hit.text,
                score=hit.score,
            )
            for hit in hits
        ],
    )
