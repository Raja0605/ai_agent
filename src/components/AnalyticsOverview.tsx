import React from 'react';
import { 
  BarChart3, 
  Clock, 
  Zap, 
  Building2, 
  CheckCircle2, 
  Award, 
  TrendingUp,
  Sparkles
} from 'lucide-react';
import type { JobPost, ApplicationLog, ResumeProfile } from '../types/job';

interface AnalyticsOverviewProps {
  jobs: JobPost[];
  logs: ApplicationLog[];
  activeResume: ResumeProfile;
}

export const AnalyticsOverview: React.FC<AnalyticsOverviewProps> = ({
  jobs,
  logs,
  activeResume
}) => {
  const naukriCount = jobs.filter(j => j.platform === 'naukri').length;
  const indeedCount = jobs.filter(j => j.platform === 'indeed').length;
  const linkedinCount = jobs.filter(j => j.platform === 'linkedin').length;
  const founditCount = jobs.filter(j => j.platform === 'foundit' || j.platform === 'glassdoor').length;
  const shineCount = jobs.filter(j => j.platform === 'shine').length;

  const justNowCount = jobs.filter(j => j.postedHoursAgo <= 1.0).length;
  const oneDayCount = jobs.filter(j => j.postedHoursAgo > 1.0 && j.postedHoursAgo <= 24.0).length;
  const twoDaysCount = jobs.filter(j => j.postedHoursAgo > 24.0 && j.postedHoursAgo <= 48.0).length;
  const threeDaysCount = jobs.filter(j => j.postedHoursAgo > 48.0 && j.postedHoursAgo <= 72.0).length;

  const avgAtsScore = logs.length > 0
    ? Math.round(logs.reduce((acc, curr) => acc + curr.atsScore, 0) / logs.length)
    : 92;

  return (
    <div className="space-y-6">
      
      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">Total Fetched Jobs</span>
            <Building2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">{jobs.length}</div>
          <span className="text-[11px] text-cyan-400 flex items-center gap-1 font-medium">
            <TrendingUp className="w-3 h-3" /> Live aggregated feeds
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">Freshness (&lt;24 hrs)</span>
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">{justNowCount + oneDayCount}</div>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
            ⚡ High response probability
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">Auto-Applications Sent</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-indigo-300">{logs.length}</div>
          <span className="text-[11px] text-slate-400 block font-mono truncate">
            Resume: {activeResume.fileName}
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">Avg ATS Match Score</span>
            <Award className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-amber-400">{avgAtsScore}%</div>
          <span className="text-[11px] text-amber-400 flex items-center gap-1 font-medium">
            <Sparkles className="w-3 h-3" /> AI keyword optimized
          </span>
        </div>

      </div>

      {/* Grid: Platform Distribution & Freshness Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Platform Breakdown */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            Jobs by Platform Feed Source
          </h3>

          <div className="space-y-3">
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-blue-400">Naukri.com</span>
                <span className="text-slate-300">{naukriCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-blue-500 h-full rounded-full transition-all duration-500" style={{ width: `${(naukriCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-indigo-400">Indeed</span>
                <span className="text-slate-300">{indeedCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${(indeedCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-sky-400">LinkedIn</span>
                <span className="text-slate-300">{linkedinCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-sky-500 h-full rounded-full transition-all duration-500" style={{ width: `${(linkedinCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-amber-400">Foundit (Monster) & Glassdoor</span>
                <span className="text-slate-300">{founditCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-amber-500 h-full rounded-full transition-all duration-500" style={{ width: `${(founditCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-fuchsia-400">Shine.com</span>
                <span className="text-slate-300">{shineCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-fuchsia-500 h-full rounded-full transition-all duration-500" style={{ width: `${(shineCount / jobs.length) * 100}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Freshness Breakdown */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-400" />
            Posting Freshness Distribution
          </h3>

          <div className="space-y-3">
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-emerald-400">⚡ Just Now (&lt;1 hr)</span>
                <span className="text-slate-300">{justNowCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-emerald-400 h-full rounded-full" style={{ width: `${(justNowCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-amber-400">🔥 1 Day Ago</span>
                <span className="text-slate-300">{oneDayCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-amber-400 h-full rounded-full" style={{ width: `${(oneDayCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-indigo-400">📅 2 Days Ago</span>
                <span className="text-slate-300">{twoDaysCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-indigo-400 h-full rounded-full" style={{ width: `${(twoDaysCount / jobs.length) * 100}%` }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-cyan-400">⏳ 3 Days Ago</span>
                <span className="text-slate-300">{threeDaysCount} jobs</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div className="bg-cyan-400 h-full rounded-full" style={{ width: `${(threeDaysCount / jobs.length) * 100}%` }} />
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
