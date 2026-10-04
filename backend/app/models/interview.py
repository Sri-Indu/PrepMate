from typing import Literal

from pydantic import BaseModel, Field

Strategy = Literal[
    "follow_up",
    "harder_question",
    "reinforce_weakness",
    "same_topic",
    "new_topic",
]

InterviewStatus = Literal["in_progress", "completed"]


class AnswerEvaluation(BaseModel):
    score: int = Field(ge=0, le=10)
    correctness: int = Field(ge=0, le=10)
    depth: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    feedback: str = ""


class InterviewReport(BaseModel):
    overall_score: float
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    topics_to_revise: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class InterviewTurnResponse(BaseModel):
    session_id: str
    status: InterviewStatus
    question_number: int
    total_questions: int
    topic: str
    strategy: str
    question: str | None = None
    evaluation: AnswerEvaluation | None = None
    report: InterviewReport | None = None
    stored: bool = False


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
