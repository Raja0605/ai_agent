import React from 'react';
import { Cpu, Sparkles } from 'lucide-react';
import type { MatchResult } from '../types/job';
import { scoreBand } from '../services/aiService';

/**
 * The match score, with its band and its provenance.
 *
 * Three things this fixes at once: the score used to be a hardcoded 85 read
 * off a `job.atsMatchScore` field that did not exist on the type; the label
 * said "Strong Match" regardless of the number; and an AI verdict and a
 * keyword heuristic were displayed identically. The icon distinguishes them
 * and the tooltip explains which is which.
 */

interface MatchBadgeProps {
  match?: MatchResult;
  isLoading?: boolean;
  size?: 'sm' | 'md';
}

export const MatchBadge: React.FC<MatchBadgeProps> = ({ match, isLoading, size = 'sm' }) => {
  if (isLoading) {
    return (
      <span className="px-3 py-1 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-500 animate-pulse">
        Scoring…
      </span>
    );
  }

  // No resume, or not scored yet. Saying so beats showing a number we made up.
  if (!match) {
    return (
      <span
        className="px-3 py-1 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-500"
        title="Upload a resume to score this job against your profile."
      >
        Not scored
      </span>
    );
  }

  const band = scoreBand(match.score);
  const isAi = match.method === 'ai';
  const Icon = isAi ? Sparkles : Cpu;

  return (
    <span
      className={`flex items-center gap-1.5 px-3 py-1 rounded-xl border ${band.tone.bg} ${band.tone.border}`}
      title={
        isAi
          ? `AI evaluation (${match.confidence} confidence). ${match.reason || ''}`
          : `Keyword-based score, no AI involved (${match.confidence} confidence). ${match.reason || ''}`
      }
    >
      <Icon className={`w-3.5 h-3.5 ${band.tone.text}`} />
      <span className={`font-bold ${band.tone.text} ${size === 'md' ? 'text-sm' : 'text-xs'}`}>
        {match.score}%
      </span>
      <span className="text-[11px] text-slate-400">{band.label}</span>
    </span>
  );
};
