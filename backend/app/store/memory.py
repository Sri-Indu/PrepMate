"""Process-wide in-memory stores. Resume PDFs are never written to disk."""

from app.services.interview import InterviewSession
from app.services.rag import InMemoryRagStore

rag_store = InMemoryRagStore()
interview_sessions: dict[str, InterviewSession] = {}
