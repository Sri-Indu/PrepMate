from pydantic import BaseModel, Field


class LlmGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    system: str | None = Field(default=None, max_length=4000)


class LlmGenerateResponse(BaseModel):
    model: str
    text: str
    provider: str = "ollama"
