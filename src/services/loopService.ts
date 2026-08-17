import type { JobLoop, LoopMatch, LoopRunResult } from '../types/job';
import { API_BASE_URL, fetchWithRetry } from '../config/api';
import { mapJob } from './jobService';

function mapLoop(data: Record<string, any>): JobLoop {
  return {
    id: data.id,
    name: data.name,
    keywords: data.keywords || [],
    location: data.location ?? null,
    remoteOnly: Boolean(data.remote_only),
    resumeId: data.resume_id ?? null,
    cadenceHours: data.cadence_hours,
    minScore: data.min_score,
    active: Boolean(data.active),
    lastRunAt: data.last_run_at ?? null,
    lastRunStatus: data.last_run_status ?? null,
    lastRunError: data.last_run_error ?? null,
    createdAt: data.created_at,
    totalMatches: data.total_matches ?? 0,
    newMatches: data.new_matches ?? 0,
  };
}

function mapMatch(data: Record<string, any>): LoopMatch {
  const job = data.job || {};
  return {
    id: data.id,
    loopId: data.loop_id,
    score: data.score,
    scoreMethod: data.score_method === 'ai' ? 'ai' : 'heuristic',
    matchedSkills: data.matched_skills || [],
    missingSkills: data.missing_skills || [],
    seen: Boolean(data.seen),
    createdAt: data.created_at,
    // The loop endpoint returns a flattened job, so it is reshaped into the
    // structure mapJob expects rather than duplicating the mapping logic.
    job: mapJob({
      ...job,
      skills: job.skills || [],
      source_records: (job.sources || []).map((source: string) => ({
        source,
        apply_url: job.apply_url,
        job_url: job.apply_url,
      })),
    }),
  };
}

export async function listLoops(): Promise<JobLoop[]> {
  const response = await fetchWithRetry(`${API_BASE_URL}/loops/`);
  if (!response.ok) throw new Error(`Could not load loops (${response.status})`);
  return (await response.json()).map(mapLoop);
}

export async function createLoop(input: {
  name: string;
  keywords: string[];
  location?: string | null;
  remoteOnly: boolean;
  cadenceHours: number;
  minScore: number;
}): Promise<JobLoop> {
  const response = await fetch(`${API_BASE_URL}/loops/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: input.name,
      keywords: input.keywords,
      location: input.location || null,
      remote_only: input.remoteOnly,
      cadence_hours: input.cadenceHours,
      min_score: input.minScore,
    }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail?.[0]?.msg || detail.detail || 'Could not create this loop.');
  }
  return mapLoop(await response.json());
}

export async function updateLoop(id: string, changes: Partial<JobLoop>): Promise<JobLoop> {
  const payload: Record<string, unknown> = {};
  if (changes.name !== undefined) payload.name = changes.name;
  if (changes.keywords !== undefined) payload.keywords = changes.keywords;
  if (changes.location !== undefined) payload.location = changes.location;
  if (changes.remoteOnly !== undefined) payload.remote_only = changes.remoteOnly;
  if (changes.cadenceHours !== undefined) payload.cadence_hours = changes.cadenceHours;
  if (changes.minScore !== undefined) payload.min_score = changes.minScore;
  if (changes.active !== undefined) payload.active = changes.active;

  const response = await fetch(`${API_BASE_URL}/loops/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`Could not update this loop (${response.status})`);
  return mapLoop(await response.json());
}

export async function deleteLoop(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/loops/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Could not delete this loop (${response.status})`);
}

export async function runLoop(id: string): Promise<LoopRunResult> {
  const response = await fetch(`${API_BASE_URL}/loops/${id}/run`, { method: 'POST' });
  if (!response.ok) throw new Error(`Could not run this loop (${response.status})`);

  const data = await response.json();
  return {
    loopId: data.loop_id,
    status: data.status,
    jobsFetched: data.jobs_fetched,
    newMatches: data.new_matches,
    belowThreshold: data.below_threshold,
    error: data.error,
  };
}

export async function getLoopMatches(id: string, unseenOnly = false): Promise<LoopMatch[]> {
  const params = new URLSearchParams({ unseen_only: String(unseenOnly) });
  const response = await fetch(`${API_BASE_URL}/loops/${id}/matches?${params}`);
  if (!response.ok) throw new Error(`Could not load matches (${response.status})`);
  return (await response.json()).map(mapMatch);
}

export async function markMatchesSeen(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/loops/${id}/matches/seen`, { method: 'POST' });
  if (!response.ok) throw new Error(`Could not mark matches as seen (${response.status})`);
}
