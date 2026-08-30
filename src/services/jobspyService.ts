import { API_BASE_URL, fetchWithRetry } from '../config/api';
import { mapJob } from './jobService';
import type { JobPost } from '../types/job';

export interface JobSpyToolInfo {
  status: string;
  server?: string;
  host?: string;
  port?: number;
  tools?: Array<{ name?: string; description?: string; inputSchema?: Record<string, unknown> }>;
  sites?: string[];
  job_search_tool?: string | null;
  input_schema?: Record<string, unknown>;
  tool_count?: number;
}

export interface JobSpyPortalStatus {
  status: 'success' | 'failed' | string;
  count: number;
  message?: string;
}

export interface JobSpySearchResponse {
  results: JobPost[];
  sources: Record<string, number>;
  portal_status: Record<string, JobSpyPortalStatus>;
  total: number;
  sites: string[];
}

export async function jobspyHealth(): Promise<JobSpyToolInfo> {
  const response = await fetchWithRetry(`${API_BASE_URL}/jobspy/health`);
  if (!response.ok) throw new Error('Job Spy MCP is unavailable');
  return response.json();
}

export async function jobspyTools(): Promise<JobSpyToolInfo> {
  const response = await fetchWithRetry(`${API_BASE_URL}/jobspy/tools`);
  if (!response.ok) throw new Error('Job Spy MCP is unavailable');
  return response.json();
}

export async function jobspyTest(): Promise<JobSpyToolInfo> {
  const response = await fetchWithRetry(`${API_BASE_URL}/jobspy/test`, { method: 'POST' });
  if (!response.ok) throw new Error('Job Spy MCP is unavailable');
  return response.json();
}

export async function jobspySearch(payload: Record<string, unknown>): Promise<JobSpySearchResponse> {
  const response = await fetch(`${API_BASE_URL}/jobspy/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Job Spy search is unavailable');
  }
  const data = await response.json();
  return {
    results: (data.results || []).map(mapJob),
    sources: data.sources || {},
    portal_status: data.portal_status || {},
    total: data.total ?? (data.results || []).length,
    sites: data.sites || [],
  };
}
