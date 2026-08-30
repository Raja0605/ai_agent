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
  showMatchDetails?: boolean;
}

const FreshnessPill: React.FC<{ hours: number | null; label: string }> = ({ hours, label }) => {
  // An unknown posting date is stated, not disguised as "just now" — which is
  // exactly what happened when postedHoursAgo was hardcoded to 0.
  if (hours === null) {
    return (
      <span className="px-2.5 py-1 text-[11px] font-medium bg-gray-100 text-gray-500 border border-gray-300 rounded-full flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Date unknown
      </span>
    );
  }

  if (hours <= 1) {
    return (
      <span className="px-2.5 py-1 text-[11px] font-bold bg-green-100 text-green-700 border border-green-300 rounded-full flex items-center gap-1">
        <Zap className="w-3 h-3 text-green-600" />
        Just now
      </span>
    );
  }

  const tone =
    hours <= 24
      ? 'bg-amber-100 text-amber-700 border-amber-300'
      : hours <= 72
        ? 'bg-blue-100 text-blue-700 border-blue-300'
        : 'bg-gray-100 text-gray-600 border-gray-300';

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
  showMatchDetails,
}) => {
  const resumeSkills = activeResume?.skills ?? [];

  return (
    <div className="relative group min-h-[330px] bg-white border border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all duration-200 rounded-xl p-5 flex flex-col justify-between gap-4 card-shadow card-shadow-hover">

      {/* Meta row: where it came from, how old it is, how well it fits */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge source={job.platform} allSources={job.sources} />
          <FreshnessPill hours={job.postedHoursAgo} label={job.postedTime} />
        </div>
        <MatchBadge match={job.match} isLoading={isScoring} />
      </div>

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors leading-snug">
          {job.title}
        </h2>

        <div className="flex items-center gap-4 text-xs text-gray-600 flex-wrap">
          <span className="flex items-center gap-1.5 font-medium text-gray-800">
            <Building2 className="w-3.5 h-3.5 text-blue-600" />
            {job.company}
          </span>
          <span className="flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-gray-500" />
            {job.location}
          </span>
          {job.isRemote && (
            <span className="flex items-center gap-1 text-green-600 font-medium">
              <Globe className="w-3.5 h-3.5" />
              Remote
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs font-medium pt-1 flex-wrap">
          <span className="flex items-center gap-1 text-gray-700 bg-gray-50 px-2.5 py-1 rounded-lg border border-gray-200">
            <Wallet className="w-3.5 h-3.5 text-green-600" />
            {job.salary}
          </span>
          <span className="flex items-center gap-1 text-gray-600 bg-gray-50 px-2.5 py-1 rounded-lg border border-gray-200">
            <Briefcase className="w-3.5 h-3.5 text-purple-600" />
            {job.experienceRequired}
          </span>
        </div>
      </div>

      <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">{job.description}</p>

      {job.skillsRequired.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider block">
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
                  className={`text-[11px] px-2.5 py-0.5 rounded-md border font-sans transition-all ${
                    isMatch
                      ? 'bg-blue-50 border-blue-300 text-blue-700 font-medium'
                      : 'bg-gray-50 border-gray-200 text-gray-600'
                  }`}
                >
                  {isMatch && '✓ '}
                  {skill}
                </span>
              );
            })}
            {job.skillsRequired.length > 8 && (
              <span className="text-[11px] text-gray-500">
                +{job.skillsRequired.length - 8} more
              </span>
            )}
          </div>
        </div>
      )}

      {showMatchDetails && job.match && (
        <div className="space-y-2 rounded-lg border border-gray-100 bg-gray-50 p-3">
          {job.match.matchReasons && job.match.matchReasons.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Why this matches</p>
              <ul className="mt-1 space-y-0.5">
                {job.match.matchReasons.slice(0, 6).map(reason => (
                  <li key={reason} className="text-[11px] text-emerald-700">✓ {reason}</li>
                ))}
              </ul>
            </div>
          )}
          {job.match.gaps && job.match.gaps.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Potential gaps</p>
              <ul className="mt-1 space-y-0.5">
                {job.match.gaps.slice(0, 4).map(gap => (
                  <li key={gap} className="text-[11px] text-amber-700">• {gap}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="h-[1px] bg-gray-200" />

      <div className="flex items-center justify-between gap-3">
        <a
          href={job.applyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View details
        </a>

        <button
          onClick={() => onOpen(job)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            isApplied
              ? 'bg-green-50 border border-green-300 text-green-700 hover:bg-green-100'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isApplied ? (
            <>
              <CheckCircle className="w-4 h-4" />
              Tracked
            </>
          ) : (
            'Save'
          )}
        </button>
      </div>
    </div>
  );
};
