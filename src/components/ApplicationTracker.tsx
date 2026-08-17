import React from 'react';
import { Building2, Calendar, FileText, Send, Sparkles } from 'lucide-react';
import type { ApplicationLog, ApplicationStatus } from '../types/job';
import { SourceBadge } from './SourceBadge';
import { scoreBand } from '../services/aiService';

interface ApplicationTrackerProps {
  logs: ApplicationLog[];
  onStatusChange: (id: string, newStatus: ApplicationStatus) => void;
}

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: 'SAVED', label: 'Saved' },
  { value: 'READY_TO_APPLY', label: 'Ready to apply' },
  { value: 'APPLYING', label: 'Applying' },
  { value: 'APPLIED', label: 'Applied' },
  { value: 'INTERVIEW', label: 'Interview' },
  { value: 'OFFER', label: 'Offer' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'WITHDRAWN', label: 'Withdrawn' },
];

function statusColor(status: ApplicationStatus): string {
  switch (status) {
    case 'APPLIED':
    case 'APPLYING':
      return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    case 'INTERVIEW':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    case 'OFFER':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
    case 'REJECTED':
    case 'FAILED':
      return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
    default:
      return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
  }
}

function formatDate(iso: string): string {
  if (!iso) return 'Not recorded';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleString();
}

export const ApplicationTracker: React.FC<ApplicationTrackerProps> = ({ logs, onStatusChange }) => (
  <div className="space-y-6">
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
          <Send className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-100">Application tracker</h2>
          {/* Was "resumes auto-submitted to Naukri, Indeed & LinkedIn" — the
              app has never submitted anything anywhere. */}
          <p className="text-xs text-slate-400">
            Jobs you opened from here. Keep the status current — the analytics are built from it.
          </p>
        </div>
      </div>

      <span className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 font-semibold">
        {logs.length} tracked
      </span>
    </div>

    {logs.length === 0 ? (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
        <Send className="w-8 h-8 text-slate-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-300">Nothing tracked yet</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Open a job from the Jobs or Loops tab, review its application kit, and it will be
          recorded here when you launch the listing.
        </p>
      </div>
    ) : (
      <div className="space-y-4">
        {logs.map(log => {
          const band = log.matchScore !== null ? scoreBand(log.matchScore) : null;
          return (
            <div
              key={log.id}
              className="bg-slate-900/80 hover:bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4 transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SourceBadge source={log.platform} />
                    <h3 className="text-sm font-bold text-slate-100">{log.jobTitle}</h3>
                    <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5" />
                      {log.company}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      {formatDate(log.appliedAt)}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-cyan-400" />
                      {log.resumeUsed}
                    </span>
                    {/* "Not scored" rather than a 0% that reads like a verdict. */}
                    <span className="flex items-center gap-1">
                      <Sparkles className={`w-3.5 h-3.5 ${band ? band.tone.text : 'text-slate-600'}`} />
                      {band ? (
                        <span className={band.tone.text}>
                          {log.matchScore}% {band.label.toLowerCase()}
                        </span>
                      ) : (
                        <span className="text-slate-500">Not scored</span>
                      )}
                    </span>
                  </div>
                </div>

                <select
                  value={log.status}
                  onChange={e => onStatusChange(log.id, e.target.value as ApplicationStatus)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-bold focus:outline-none cursor-pointer shrink-0 ${statusColor(log.status)}`}
                >
                  {STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value} className="bg-slate-900 text-slate-200">
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {log.coverNote && (
                <details className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                  <summary className="text-[11px] text-indigo-400 font-semibold cursor-pointer">
                    Cover note prepared for this application
                  </summary>
                  <p className="text-[11px] text-slate-400 mt-2 whitespace-pre-wrap">{log.coverNote}</p>
                </details>
              )}
            </div>
          );
        })}
      </div>
    )}
  </div>
);
