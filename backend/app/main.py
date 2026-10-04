"""FastAPI application entrypoint.

PDF extraction, in-memory RAG, local Ollama generation, candidate analysis,
and a two-question adaptive interview are available.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import router as analysis_router
from app.api.documents import router as documents_router
from app.api.interview import router as interview_router
from app.api.llm import router as llm_router
from app.api.rag import router as rag_router
from app.core.config import settings
from app.models.health import HealthResponse

app = FastAPI(
    title="PrepMate API",
    description="Interview preparation companion backend.",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(llm_router)
app.include_router(analysis_router)
app.include_router(interview_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check used by local testing and later by the frontend."""
    return HealthResponse(
        status="ok",
        service="prepmate-backend",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )
