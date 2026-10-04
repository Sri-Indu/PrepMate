export type CandidateAnalysis = {
  summary: string;
  strengths: string[];
  skill_gaps: string[];
  relevant_experience: string[];
  interview_topics: string[];
  preparation_plan: string[];
  model: string;
  stored: boolean;
};

export type AnswerEvaluation = {
  score: number;
  correctness: number;
  depth: number;
  clarity: number;
  completeness: number;
  strengths: string[];
  missing_concepts: string[];
  feedback: string;
};

export type InterviewReport = {
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  topics_to_revise: string[];
  recommended_next_steps: string[];
};

export type InterviewTurn = {
  session_id: string;
  status: "in_progress" | "completed";
  question_number: number;
  total_questions: number;
  topic: string;
  strategy: string;
  question: string | null;
  evaluation: AnswerEvaluation | null;
  report: InterviewReport | null;
  stored: boolean;
};
