import { API_BASE_URL } from '../config/api';
import { mapJob } from './jobService';
import type { JobPost, MatchResult } from '../types/job';

export interface InterpretedPrompt {
  prompt: string;
  keywords: string[];
  skills: string[];
  locations: string[];
  country: string | null;
  remote: boolean | null;
  hybrid: boolean;
  experience_min: number | null;
  experience_max: number | null;
  salary_min: number | null;
  job_type: string | null;
  hours_old: number | null;
  company: string | null;
}

export interface PromptAISourceStatus {
  status: string;
  count: number;
  message?: string | null;
}

export interface PromptAISearchResponse {
  interpreted: InterpretedPrompt;
  results: JobPost[];
  source_status: Record<string, PromptAISourceStatus>;
  progress: string[];
  total: number;
  resume_id: string;
  resume_file_name: string;
}

function mapMatch(raw: Record<string, any> | undefined): MatchResult | undefined {
  if (!raw) return undefined;
  return {
    score: raw.score ?? 0,
    matchedSkills: raw.matched_skills || [],
    missingSkills: raw.missing_skills || [],
    summary: raw.summary || '',
    recommendations: raw.recommendations || [],
    reason: raw.reason,
    method: 'heuristic',
    confidence: raw.confidence || 'low',
    matchReasons: raw.match_reasons || [],
    gaps: raw.gaps || [],
  };
}

function mapPayload(data: Record<string, any>): PromptAISearchResponse {
  return {
    interpreted: data.interpreted,
    results: (data.results || []).map((job: Record<string, any>) => ({
      ...mapJob(job),
      match: mapMatch(job.match),
    })),
    source_status: data.source_status || {},
    progress: data.progress || [],
    total: data.total ?? (data.results || []).length,
    resume_id: data.resume_id,
    resume_file_name: data.resume_file_name,
  };
}

export async function promptAiSearch(
  prompt: string,
  resumeId: string,
  onProgress?: (message: string) => void,
): Promise<PromptAISearchResponse> {
  const response = await fetch(`${API_BASE_URL}/prompt-ai/search?stream=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ prompt, resume_id: resumeId }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Prompt AI search failed (${response.status})`);
  }

  if (!response.body) {
    throw new Error('Prompt AI search returned no response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let complete: PromptAISearchResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    for (const part of parts) {
      const line = part.split('\n').find(row => row.startsWith('data: '));
      if (!line) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.event === 'progress' && payload.message) {
        onProgress?.(payload.message);
      } else if (payload.event === 'complete') {
        complete = mapPayload(payload.data);
      } else if (payload.event === 'error') {
        throw new Error(payload.message || 'Prompt AI search failed');
      }
    }
  }

  if (!complete) {
    throw new Error('Prompt AI search ended without results');
  }
  return complete;
}
