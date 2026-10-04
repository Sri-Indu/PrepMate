from pydantic import BaseModel, Field


class CandidateAnalysis(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    relevant_experience: list[str] = Field(default_factory=list)
    interview_topics: list[str] = Field(default_factory=list)
    preparation_plan: list[str] = Field(default_factory=list)
    model: str
    stored: bool = Field(
        description="Always false: the resume PDF is not saved."
    )
