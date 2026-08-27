import type { AtsCheckResult } from '../types/job';

export function scoreBand(score: number) {
  if (score >= 80) return { label: 'Strong match', tone: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400' } };
  if (score >= 60) return { label: 'Good match', tone: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', text: 'text-cyan-400' } };
  return { label: 'Partial match', tone: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400' } };
}

/** Deterministic document-structure check; no external service or model call. */
export async function checkResumeStructure(resume: { rawText?: string }): Promise<AtsCheckResult> {
  const text = resume.rawText || '';
  const sections = ['experience', 'education', 'skills', 'summary'].filter(section => new RegExp(`\\b${section}\\b`, 'i').test(text));
  const issues = text.trim() ? [] : [{ severity: 'warning' as const, message: 'Resume text is unavailable.', fix: 'Upload or paste a text-readable resume.' }];
  return { score: text.trim() ? Math.min(100, 55 + sections.length * 10) : 0, issues, detectedSections: sections, wordCount: text.trim() ? text.trim().split(/\s+/).length : 0 };
}
