from pydantic import BaseModel, Field


class RagIndexRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    job_description_text: str = Field(min_length=1)


class RagIndexResponse(BaseModel):
    resume_chunks: int
    job_description_chunks: int
    total_chunks: int
    persisted: bool = Field(
        description="Always false: vectors and text stay in memory only."
    )


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=20)


class RagHit(BaseModel):
    chunk_id: int
    source: str
    text: str
    score: float


class RagQueryResponse(BaseModel):
    query: str
    hits: list[RagHit]
