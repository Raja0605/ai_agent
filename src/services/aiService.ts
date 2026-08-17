import type {
  AiRuntimeConfig,
  AtsCheckResult,
  JobPost,
  MatchResult,
  ResumeProfile,
  TailorResult,
} from '../types/job';
import { API_BASE_URL, fetchWithRetry } from '../config/api';

/**
 * Score bands.
 *
 * The detail panel used to render `Strong Match (${score}%)` unconditionally,
 * in emerald, for every job — including a 12% match. A score is only useful
 * if its label changes with it.
 */
export type ScoreBand = {
  label: string;
  /** Tailwind classes for text / background / border, in that order. */
  tone: { text: string; bg: string; border: string };
};

export function scoreBand(score: number): ScoreBand {
  if (score >= 80) {
    return {
      label: 'Strong match',
      tone: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
    };
  }
  if (score >= 60) {
    return {
      label: 'Good match',
      tone: { text: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30' },
    };
  }
  if (score >= 40) {
    return {
      label: 'Partial match',
      tone: { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
    };
  }
  return {
    label: 'Weak match',
    tone: { text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' },
  };
}

function toResumePayload(resume: ResumeProfile) {
  return {
    full_name: resume.fullName,
    target_role: resume.targetRole,
    summary: resume.summary,
    skills: resume.skills,
    experience_years: resume.experienceYears,
    raw_text: resume.rawText,
  };
}

function toMatchResult(data: Record<string, any>): MatchResult {
  return {
    score: data.score,
    matchedSkills: data.matched_skills || [],
    missingSkills: data.missing_skills || [],
    summary: data.summary || '',
    recommendations: data.recommendations || [],
    reason: data.reason,
    method: data.method === 'ai' ? 'ai' : 'heuristic',
    confidence: data.confidence || 'medium',
  };
}

export async function getAiConfig(): Promise<AiRuntimeConfig> {
  const response = await fetchWithRetry(`${API_BASE_URL}/ai/config`);
  if (!response.ok) throw new Error(`Could not read AI config (${response.status})`);

  const data = await response.json();
  return {
    provider: data.provider,
    providerName: data.provider_name,
    model: data.model,
    configured: Boolean(data.configured),
    activeMethod: data.active_method === 'ai' ? 'ai' : 'heuristic',
  };
}

/** Full evaluation of one job — uses the model when one is configured. */
export async function analyzeMatch(resume: ResumeProfile, job: JobPost): Promise<MatchResult> {
  const response = await fetch(`${API_BASE_URL}/ai/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: job.id,
      job_title: job.title,
      job_description: job.description,
      job_skills: job.skillsRequired,
      company: job.company,
      resume: toResumePayload(resume),
    }),
  });

  if (!response.ok) throw new Error(`Match evaluation failed (${response.status})`);
  return toMatchResult(await response.json());
}

/**
 * Score a whole result page in one request.
 *
 * Deterministic on the server by design — one model call per card would be
 * slow and expensive for a number whose only job is to rank a list. The
 * result carries `method: 'heuristic'` and the UI labels it as such.
 */
export async function matchJobsBatch(
  resume: ResumeProfile,
  jobs: JobPost[]
): Promise<Map<string, MatchResult>> {
  if (jobs.length === 0) return new Map();

  const response = await fetch(`${API_BASE_URL}/ai/match/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resume: toResumePayload(resume),
      jobs: jobs.map(job => ({
        job_id: job.id,
        job_title: job.title,
        job_description: job.description,
        job_skills: job.skillsRequired,
        company: job.company,
      })),
    }),
  });

  if (!response.ok) throw new Error(`Batch scoring failed (${response.status})`);

  const data = await response.json();
  const results = new Map<string, MatchResult>();
  (data.items || []).forEach((item: Record<string, any>) => {
    results.set(item.job_id, toMatchResult(item.result));
  });
  return results;
}

export async function generateCoverLetter(
  resume: ResumeProfile,
  job: JobPost
): Promise<{ content: string; method: string }> {
  const response = await fetch(`${API_BASE_URL}/ai/cover-letter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: job.id,
      job_title: job.title,
      company: job.company,
      job_skills: job.skillsRequired,
      resume: toResumePayload(resume),
    }),
  });

  if (!response.ok) throw new Error(`Cover letter generation failed (${response.status})`);

  const data = await response.json();
  return { content: data.content, method: data.method };
}

export async function tailorResume(resume: ResumeProfile, job: JobPost): Promise<TailorResult> {
  const response = await fetch(`${API_BASE_URL}/ai/tailor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: job.id,
      job_title: job.title,
      company: job.company,
      job_description: job.description,
      job_skills: job.skillsRequired,
      resume: toResumePayload(resume),
    }),
  });

  if (!response.ok) throw new Error(`Resume tailoring failed (${response.status})`);

  const data = await response.json();
  return {
    tailoredSummary: data.tailored_summary,
    prioritizedSkills: data.prioritized_skills || [],
    keywordsToAdd: data.keywords_to_add || [],
    bulletSuggestions: data.bullet_suggestions || [],
    method: data.method === 'ai' ? 'ai' : 'heuristic',
  };
}

export async function checkAts(resume: ResumeProfile): Promise<AtsCheckResult> {
  const response = await fetch(`${API_BASE_URL}/ai/ats-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume: toResumePayload(resume) }),
  });

  if (!response.ok) throw new Error(`ATS check failed (${response.status})`);

  const data = await response.json();
  return {
    score: data.score,
    issues: data.issues || [],
    detectedSections: data.detected_sections || [],
    wordCount: data.word_count || 0,
  };
}
