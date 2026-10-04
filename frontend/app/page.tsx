"use client";

import { FormEvent, useState } from "react";
import {
  analyzeCandidate,
  startInterview,
  submitInterviewAnswer,
} from "@/lib/api";
import type { CandidateAnalysis, InterviewTurn } from "@/lib/types";

export default function HomePage() {
  const [jobDescription, setJobDescription] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CandidateAnalysis | null>(null);
  const [interview, setInterview] = useState<InterviewTurn | null>(null);
  const [answer, setAnswer] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setInterview(null);
    setAnswer("");

    if (!resume) {
      setError("Choose a resume PDF.");
      return;
    }
    if (jobDescription.trim().length < 30) {
      setError("Paste a job description (at least 30 characters).");
      return;
    }

    setLoading(true);
    try {
      const analysis = await analyzeCandidate(resume, jobDescription.trim());
      setResult(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onStartInterview() {
    if (!resume) {
      setError("Choose a resume PDF.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const turn = await startInterview(resume, jobDescription.trim());
      setInterview(turn);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start interview.");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmitAnswer(event: FormEvent) {
    event.preventDefault();
    if (!interview) {
      return;
    }
    if (!answer.trim()) {
      setError("Write an answer before submitting.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const turn = await submitInterviewAnswer(interview.session_id, answer.trim());
      setInterview(turn);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit answer.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm font-medium text-slate-500">PrepMate</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
        Analyze your fit
      </h1>
      <p className="mt-3 text-slate-600">
        Upload a resume PDF and paste a job description. Local Gemma 2B uses
        retrieved resume and JD context. The PDF is not stored.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block">
          <span className="text-sm font-medium text-slate-800">Resume (PDF)</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            className="mt-2 block w-full text-sm text-slate-700"
            onChange={(event) => setResume(event.target.files?.[0] ?? null)}
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-800">Job description</span>
          <textarea
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            rows={8}
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-slate-900"
            placeholder="Paste the target job description…"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {loading && !interview ? "Analyzing…" : "Analyze My Fit"}
        </button>
      </form>

      {error ? (
        <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">
          Working with local RAG and Gemma 2B. This can take a minute.
        </p>
      ) : null}

      {result ? (
        <AnalysisResult
          result={result}
          onStartInterview={onStartInterview}
          loading={loading}
          interviewStarted={interview !== null}
        />
      ) : null}

      {interview ? (
        <InterviewPanel
          interview={interview}
          answer={answer}
          loading={loading}
          onAnswerChange={setAnswer}
          onSubmitAnswer={onSubmitAnswer}
        />
      ) : null}
    </main>
  );
}

function AnalysisResult({
  result,
  onStartInterview,
  loading,
  interviewStarted,
}: {
  result: CandidateAnalysis;
  onStartInterview: () => void;
  loading: boolean;
  interviewStarted: boolean;
}) {
  return (
    <section className="mt-8 space-y-6">
      <p className="text-sm text-slate-500">
        Model: {result.model}
        {result.stored ? "" : " · Resume not stored"}
      </p>
      <p className="text-slate-800">{result.summary}</p>
      <ResultList title="Strengths" items={result.strengths} />
      <ResultList title="Skill Gaps" items={result.skill_gaps} />
      <ResultList title="Relevant Experience" items={result.relevant_experience} />
      <ResultList title="Interview Topics" items={result.interview_topics} />
      <ResultList title="Preparation Plan" items={result.preparation_plan} />
      {!interviewStarted ? (
        <button
          type="button"
          onClick={onStartInterview}
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {loading ? "Starting…" : "Start Mock Interview"}
        </button>
      ) : null}
    </section>
  );
}

function InterviewPanel({
  interview,
  answer,
  loading,
  onAnswerChange,
  onSubmitAnswer,
}: {
  interview: InterviewTurn;
  answer: string;
  loading: boolean;
  onAnswerChange: (value: string) => void;
  onSubmitAnswer: (event: FormEvent) => void;
}) {
  return (
    <section className="mt-8 space-y-5 rounded-xl border border-slate-200 bg-white p-6">
      <p className="text-sm text-slate-500">
        Question {interview.question_number} of {interview.total_questions}
        {" · "}
        Topic: {interview.topic}
        {" · "}
        Strategy: {interview.strategy}
      </p>

      {interview.question ? (
        <p className="text-lg font-medium text-slate-900">{interview.question}</p>
      ) : null}

      {interview.evaluation ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
          <p className="font-medium">Last evaluation</p>
          <p className="mt-1">
            Score {interview.evaluation.score}/10 · correctness{" "}
            {interview.evaluation.correctness} · depth {interview.evaluation.depth} ·
            clarity {interview.evaluation.clarity} · completeness{" "}
            {interview.evaluation.completeness}
          </p>
          <p className="mt-2">{interview.evaluation.feedback}</p>
        </div>
      ) : null}

      {interview.status === "in_progress" && interview.question ? (
        <form onSubmit={onSubmitAnswer} className="space-y-3">
          <textarea
            value={answer}
            onChange={(event) => onAnswerChange(event.target.value)}
            rows={6}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-slate-900"
            placeholder="Type your answer…"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {loading ? "Scoring…" : "Submit Answer"}
          </button>
        </form>
      ) : null}

      {interview.report ? (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">Final feedback</h2>
          <p className="text-slate-800">Overall score: {interview.report.overall_score}/10</p>
          <ResultList title="Strengths" items={interview.report.strengths} />
          <ResultList title="Weaknesses" items={interview.report.weaknesses} />
          <ResultList title="Topics to revise" items={interview.report.topics_to_revise} />
          <ResultList title="Recommended next steps" items={interview.report.recommended_next_steps} />
        </div>
      ) : null}
    </section>
  );
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">None returned.</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-800">
          {items.map((item) => (
            <li key={`${title}-${item}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
