import React from 'react';
import {
  Briefcase,
  Building2,
  CheckCircle,
  Clock,
  ExternalLink,
  Globe,
  MapPin,
  Wallet,
  Zap,
} from 'lucide-react';
import type { JobPost, ResumeProfile } from '../types/job';
import { MatchBadge } from './MatchBadge';
import { SourceBadge } from './SourceBadge';

interface JobCardProps {
  job: JobPost;
  activeResume: ResumeProfile | null;
  isApplied: boolean;
  isScoring?: boolean;
  onOpen: (job: JobPost) => void;
}

const FreshnessPill: React.FC<{ hours: number | null; label: string }> = ({ hours, label }) => {
  // An unknown posting date is stated, not disguised as "just now" — which is
  // exactly what happened when postedHoursAgo was hardcoded to 0.
  if (hours === null) {
    return (
      <span className="px-2.5 py-1 text-[11px] font-medium bg-slate-900 text-slate-500 border border-slate-800 rounded-full flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Date unknown
      </span>
    );
  }

  if (hours <= 1) {
    return (
      <span className="px-2.5 py-1 text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-full flex items-center gap-1">
        <Zap className="w-3 h-3 text-emerald-400" />
        Just now
      </span>
    );
  }

  const tone =
    hours <= 24
      ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
      : hours <= 72
        ? 'bg-slate-800 text-cyan-300 border-cyan-500/30'
        : 'bg-slate-900 text-slate-400 border-slate-800';

  return (
    <span className={`px-2.5 py-1 text-[11px] font-medium rounded-full border flex items-center gap-1 ${tone}`}>
      <Clock className="w-3 h-3" />
      {label}
    </span>
  );
};

export const JobCard: React.FC<JobCardProps> = ({
  job,
  activeResume,
  isApplied,
  isScoring,
  onOpen,
}) => {
  const resumeSkills = activeResume?.skills ?? [];

  return (
    <div className="relative group bg-slate-900/70 hover:bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition-all duration-300 rounded-2xl p-6 flex flex-col justify-between gap-4 shadow-xl">

      {/* Meta row: where it came from, how old it is, how well it fits */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge source={job.platform} allSources={job.sources} />
          <FreshnessPill hours={job.postedHoursAgo} label={job.postedTime} />
        </div>
        <MatchBadge match={job.match} isLoading={isScoring} />
      </div>

      <div className="space-y-2">
        <h2 className="text-lg font-bold text-slate-100 group-hover:text-cyan-300 transition-colors leading-snug">
          {job.title}
        </h2>

        <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
          <span className="flex items-center gap-1.5 font-semibold text-slate-200">
            <Building2 className="w-3.5 h-3.5 text-cyan-400" />
            {job.company}
          </span>
          <span className="flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-slate-500" />
            {job.location}
          </span>
          {job.isRemote && (
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <Globe className="w-3.5 h-3.5" />
              Remote
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs font-medium pt-1 flex-wrap">
          <span className="flex items-center gap-1 text-slate-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
            <Wallet className="w-3.5 h-3.5 text-emerald-400" />
            {job.salary}
          </span>
          <span className="flex items-center gap-1 text-slate-400 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
            <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
            {job.experienceRequired}
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{job.description}</p>

      {job.skillsRequired.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
            Listed requirements
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {job.skillsRequired.slice(0, 8).map(skill => {
              const isMatch = resumeSkills.some(
                rs =>
                  rs.toLowerCase().includes(skill.toLowerCase()) ||
                  skill.toLowerCase().includes(rs.toLowerCase())
              );
              return (
                <span
                  key={skill}
                  className={`text-[11px] px-2.5 py-0.5 rounded-md border font-mono transition-all ${
                    isMatch
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300 font-semibold'
                      : 'bg-slate-950/80 border-slate-800 text-slate-500'
                  }`}
                >
                  {isMatch && '✓ '}
                  {skill}
                </span>
              );
            })}
            {job.skillsRequired.length > 8 && (
              <span className="text-[11px] text-slate-500">
                +{job.skillsRequired.length - 8} more
              </span>
            )}
          </div>
        </div>
      )}

      <div className="h-[1px] bg-slate-800/80" />

      <div className="flex items-center justify-between gap-3">
        <a
          href={job.applyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View listing
        </a>

        <button
          onClick={() => onOpen(job)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            isApplied
              ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30'
              : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20'
          }`}
        >
          {isApplied ? (
            <>
              <CheckCircle className="w-4 h-4" />
              Tracked
            </>
          ) : (
            'Prepare application'
          )}
        </button>
      </div>
    </div>
  );
};
