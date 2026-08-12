import React from 'react';
import { 
  Building2, 
  MapPin, 
  DollarSign, 
  Clock, 
  ExternalLink, 
  Send, 
  CheckCircle, 
  Sparkles,
  Zap,
  Globe,
  Briefcase
} from 'lucide-react';
import type { JobPost, Platform, ResumeProfile } from '../types/job';

interface JobCardProps {
  job: JobPost;
  activeResume: ResumeProfile;
  isApplied: boolean;
  onApplyClick: (job: JobPost) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  activeResume,
  isApplied,
  onApplyClick
}) => {
  const getPlatformBadge = (platform: Platform) => {
    switch (platform) {
      case 'naukri':
        return (
          <span className="px-2.5 py-1 text-[11px] font-bold bg-blue-500/15 border border-blue-500/30 text-blue-300 rounded-lg flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            Naukri.com
          </span>
        );
      case 'indeed':
        return (
          <span className="px-2.5 py-1 text-[11px] font-bold bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 rounded-lg flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            Indeed
          </span>
        );
      case 'linkedin':
        return (
          <span className="px-2.5 py-1 text-[11px] font-bold bg-sky-500/15 border border-sky-500/30 text-sky-300 rounded-lg flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            LinkedIn
          </span>
        );
      case 'foundit':
        return (
          <span className="px-2.5 py-1 text-[11px] font-bold bg-amber-500/15 border border-amber-500/30 text-amber-300 rounded-lg flex items-center gap-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            Foundit
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 text-[11px] font-bold bg-slate-800 border border-slate-700 text-slate-300 rounded-lg">
            Job Portal
          </span>
        );
    }
  };

  const getFreshnessPill = () => {
    if (job.postedHoursAgo <= 1.0) {
      return (
        <span className="px-2.5 py-1 text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-full flex items-center gap-1 animate-pulse shadow-md shadow-emerald-500/10">
          <Zap className="w-3 h-3 text-emerald-400" />
          Just Now
        </span>
      );
    }
    if (job.postedHoursAgo <= 24.0) {
      return (
        <span className="px-2.5 py-1 text-[11px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded-full flex items-center gap-1">
          <Clock className="w-3 h-3 text-amber-400" />
          1 Day Ago
        </span>
      );
    }
    if (job.postedHoursAgo <= 48.0) {
      return (
        <span className="px-2.5 py-1 text-[11px] font-medium bg-slate-800 text-indigo-300 border border-indigo-500/30 rounded-full flex items-center gap-1">
          <Clock className="w-3 h-3 text-indigo-400" />
          2 Days Ago
        </span>
      );
    }
    if (job.postedHoursAgo <= 72.0) {
      return (
        <span className="px-2.5 py-1 text-[11px] font-medium bg-slate-800 text-cyan-300 border border-cyan-500/30 rounded-full flex items-center gap-1">
          <Clock className="w-3 h-3 text-cyan-400" />
          3 Days Ago
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 text-[11px] font-medium bg-slate-900 text-slate-400 border border-slate-800 rounded-full flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {job.postedTime}
      </span>
    );
  };

  const atsScore = job.atsMatchScore || 85;

  return (
    <div className={`relative group bg-slate-900/70 hover:bg-slate-900/90 border transition-all duration-300 rounded-2xl p-6 flex flex-col justify-between space-y-4 shadow-xl ${
      job.featured 
        ? 'border-cyan-500/40 shadow-cyan-500/5 bg-gradient-to-b from-slate-900/90 via-slate-900/70 to-slate-950/80' 
        : 'border-slate-800 hover:border-slate-700'
    }`}>
      
      {/* Top Meta Bar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          {getPlatformBadge(job.platform)}
          {getFreshnessPill()}
        </div>

        {/* ATS Match Score Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-950/80 border border-slate-800" title={`ATS Match percentage calculated against active resume: ${activeResume.fileName}`}>
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] text-slate-400">ATS Match:</span>
          <span className={`text-xs font-bold ${
            atsScore >= 80 ? 'text-emerald-400' : atsScore >= 60 ? 'text-amber-400' : 'text-slate-400'
          }`}>
            {atsScore}%
          </span>
        </div>
      </div>

      {/* Main Body: Title & Company */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-lg font-bold text-slate-100 group-hover:text-cyan-300 transition-colors leading-snug">
            {job.title}
          </h2>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
          <span className="flex items-center gap-1.5 font-semibold text-slate-200">
            <Building2 className="w-3.5 h-3.5 text-cyan-400" />
            {job.company}
          </span>
          <span className="flex items-center gap-1 text-slate-400">
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

        {/* Salary & Experience */}
        <div className="flex items-center gap-4 text-xs font-medium pt-1 text-slate-300 flex-wrap">
          <span className="flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
            <DollarSign className="w-3.5 h-3.5" />
            {job.salary}
          </span>
          <span className="flex items-center gap-1 text-slate-400 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
            <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
            Exp: {job.experienceRequired}
          </span>
        </div>
      </div>

      {/* Description Snippet */}
      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
        {job.description}
      </p>

      {/* Skills Badges */}
      <div className="space-y-1.5 pt-1">
        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
          Required Tech Stack:
        </span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {job.skillsRequired.map(skill => {
            const isMatch = activeResume.skills.some(rs => rs.toLowerCase().includes(skill.toLowerCase()) || skill.toLowerCase().includes(rs.toLowerCase()));
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
        </div>
      </div>

      <div className="h-[1px] bg-slate-800/80" />

      {/* Action Footer */}
      <div className="flex items-center justify-between gap-3 pt-1">
        {/* Direct Link */}
        <a
          href={job.applyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View Listing
        </a>

        {/* Auto-Apply Button */}
        {isApplied ? (
          <button
            disabled
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold cursor-default"
          >
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Applied with Resume
          </button>
        ) : (
          <button
            onClick={() => onApplyClick(job)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Send className="w-3.5 h-3.5" />
            Auto-Apply with Resume
          </button>
        )}
      </div>

    </div>
  );
};
