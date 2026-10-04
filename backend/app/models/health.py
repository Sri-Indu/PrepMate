from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Service liveness: ok when the API is up.")
    service: str = Field(description="Stable identifier for this API.")
    llm_provider: str = Field(
        description="Configured LLM provider name. Not a connectivity check."
    )
    llm_model: str = Field(
        description="Configured open-weight model id (Ollama tag)."
    )
