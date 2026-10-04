"""Test helper: send a prompt to the local Ollama model."""

from fastapi import APIRouter, HTTPException

from app.models.llm import LlmGenerateRequest, LlmGenerateResponse
from app.services.llm import LlmError, generate_text

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/generate", response_model=LlmGenerateResponse)
def generate(body: LlmGenerateRequest) -> LlmGenerateResponse:
    try:
        result = generate_text(body.prompt, system=body.system)
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return LlmGenerateResponse(model=result.model, text=result.text, provider="ollama")
