import type { ResumeProfile } from '../types/job';
import { API_BASE_URL, fetchWithRetry } from '../config/api';

const ACTIVE_RESUME_KEY = 'job_pulse_active_resume_id';

/**
 * Resumes come from the backend only.
 *
 * There used to be a hardcoded "Alex Vance" DevOps resume — a fictional
 * person with a fabricated skill list and a fixed 92% ATS score — that the app
 * silently fell back to whenever the backend returned nothing. Every match
 * score, analytics figure and cover letter was then computed against a person
 * who does not exist, while the UI presented it as the user's own resume.
 * An empty vault is now an empty vault, and the UI asks for an upload.
 */

function mapResume(data: Record<string, any>): ResumeProfile {
  const skills: string[] = data.extracted_skills || [];
  const rawText: string = data.raw_text || '';

  // The backend Resume model stores no name/contact fields, so they are read
  // back out of the parsed text rather than invented.
  const emailMatch = rawText.match(/[\w.+-]+@[\w-]+\.[\w.]+/);
  const phoneMatch = rawText.match(/\+?\d[\d\s().-]{7,}\d/);
  const firstLine = rawText.split('\n').map(line => line.trim()).find(Boolean);

  return {
    id: data.id,
    fileName: data.file_name,
    uploadedAt: data.created_at ? new Date(data.created_at).toLocaleDateString() : 'Unknown',
    fileSize: rawText ? `${Math.max(1, Math.round(rawText.length / 1024))} KB of text` : 'Unknown',
    fullName: firstLine || 'Name not detected',
    email: emailMatch?.[0] || 'Not detected',
    phone: phoneMatch?.[0] || 'Not detected',
    targetRole: data.target_role || (skills.length ? `${skills[0]} specialist` : 'Not detected'),
    summary: data.summary || '',
    skills,
    experienceYears: data.experience_years ?? 0,
    education: '',
    rawText,
  };
}

export async function getStoredResumes(): Promise<ResumeProfile[]> {
  const response = await fetchWithRetry(`${API_BASE_URL}/profile/resume`);
  if (!response.ok) {
    throw new Error(`Could not load resumes (${response.status})`);
  }

  const data = await response.json();
  return Array.isArray(data) ? data.map(mapResume) : [];
}

export function getActiveResumeId(): string | null {
  return localStorage.getItem(ACTIVE_RESUME_KEY);
}

export function saveActiveResumeId(id: string): void {
  localStorage.setItem(ACTIVE_RESUME_KEY, id);
}

/** Upload a PDF and let the backend parse it. */
export async function uploadResumePdf(file: File): Promise<ResumeProfile> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/profile/resume/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed (${response.status})`);
  }

  const resume = mapResume(await response.json());
  saveActiveResumeId(resume.id);
  return resume;
}

/** Save a resume supplied as pasted plain text. */
export async function saveResumeText(rawText: string, fileName: string): Promise<ResumeProfile> {
  const response = await fetch(`${API_BASE_URL}/profile/resume/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_name: fileName, raw_text: rawText }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Could not save this resume (${response.status})`);
  }

  const resume = mapResume(await response.json());
  saveActiveResumeId(resume.id);
  return resume;
}

/**
 * Delete a resume.
 *
 * This previously did nothing at all — it reloaded the list and returned it,
 * so the deleted resume reappeared and the user was told the delete worked.
 */
export async function deleteResume(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/profile/resume/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`Could not delete this resume (${response.status})`);
  }
  if (getActiveResumeId() === id) {
    localStorage.removeItem(ACTIVE_RESUME_KEY);
  }
}
