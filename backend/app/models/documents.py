from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["resume", "job_description"]


class DocumentExtractResponse(BaseModel):
    document_type: DocumentType
    filename: str
    page_count: int = Field(ge=0)
    character_count: int = Field(ge=0)
    text: str
    stored: bool = Field(
        description="Always false: uploaded PDFs are processed in memory and discarded."
    )
