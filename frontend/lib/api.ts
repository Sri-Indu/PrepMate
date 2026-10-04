import type { CandidateAnalysis, InterviewTurn } from "./types";

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function resolveApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  // Empty string must not win: fetch("/interview/start") would hit Next.js on :3000.
  return (fromEnv || DEFAULT_API_BASE).replace(/\/$/, "");
}

export const API_BASE = resolveApiBase();

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120_000);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The request timed out. Gemma may still be loading.");
    }
    throw new Error("Could not reach the PrepMate API. Is the backend running?");
  } finally {
    clearTimeout(timer);
  }

  const payload = (await response.json().catch(() => null)) as
    | T
    | { detail?: string }
    | null;

  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed (${response.status}).`;
    throw new Error(detail);
  }

  return payload as T;
}

export async function analyzeCandidate(
  resume: File,
  jobDescription: string,
): Promise<CandidateAnalysis> {
  const body = new FormData();
  body.append("resume", resume);
  body.append("job_description", jobDescription);
  return requestJson<CandidateAnalysis>("/analysis", { method: "POST", body });
}

export async function startInterview(
  resume: File,
  jobDescription: string,
): Promise<InterviewTurn> {
  const body = new FormData();
  body.append("resume", resume);
  body.append("job_description", jobDescription);
  return requestJson<InterviewTurn>("/interview/start", { method: "POST", body });
}

export async function submitInterviewAnswer(
  sessionId: string,
  answer: string,
): Promise<InterviewTurn> {
  return requestJson<InterviewTurn>(`/interview/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
}
