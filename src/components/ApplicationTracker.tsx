import React from 'react';
import { 
  Send, 
  Building2, 
  Calendar, 
  FileText, 
  CheckCircle2, 
  Clock, 
  ExternalLink,
  Sparkles,
  Search,
  Filter
} from 'lucide-react';
import type { ApplicationLog, Platform } from '../types/job';

interface ApplicationTrackerProps {
  logs: ApplicationLog[];
  onStatusChange: (id: string, newStatus: ApplicationLog['status']) => void;
}

export const ApplicationTracker: React.FC<ApplicationTrackerProps> = ({
  logs,
  onStatusChange
}) => {
  const getPlatformBadge = (platform: Platform) => {
    switch (platform) {
      case 'naukri':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40 rounded">Naukri</span>;
      case 'indeed':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 rounded">Indeed</span>;
      case 'linkedin':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40 rounded">LinkedIn</span>;
      case 'shine':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/40 rounded">Shine</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">Foundit</span>;
    }
  };

  const getStatusColor = (status: ApplicationLog['status']) => {
    switch (status) {
      case 'Submitted':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      case 'Under Review':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'Interviewing':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'Accepted':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Send className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Application Dispatch History</h2>
            <p className="text-xs text-slate-400">Track status of resumes auto-submitted to Naukri, Indeed & LinkedIn</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Total Dispatched: <strong className="text-white">{logs.length}</strong>
          </span>
        </div>
      </div>

      {/* Logs Table / Cards */}
      {logs.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <Send className="w-8 h-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-bold text-slate-300">No Job Applications Submitted Yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Browse fetched jobs on the Jobs tab and click <strong className="text-cyan-400">Auto-Apply with Resume</strong> to trigger 1-click automated submissions.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {logs.map(log => (
            <div
              key={log.id}
              className="bg-slate-900/80 hover:bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4 transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                
                {/* Left: Info */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getPlatformBadge(log.platform)}
                    <h3 className="text-sm font-bold text-slate-100">{log.jobTitle}</h3>
                    <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5" />
                      {log.company}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      Applied: {log.appliedAt}
                    </span>
                    <span className="flex items-center gap-1 text-slate-300">
                      <FileText className="w-3.5 h-3.5 text-cyan-400" />
                      Resume Used: <strong className="text-slate-200">{log.resumeUsed}</strong>
                    </span>
                    <span className="flex items-center gap-1 text-amber-400 font-semibold">
                      <Sparkles className="w-3.5 h-3.5" />
                      ATS Score: {log.atsScore}%
                    </span>
                  </div>
                </div>

                {/* Right: Status Dropdown Selector */}
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 hidden sm:inline">Status:</span>
                  <select
                    value={log.status}
                    onChange={(e) => onStatusChange(log.id, e.target.value as ApplicationLog['status'])}
                    className={`px-3 py-1.5 rounded-xl border text-xs font-bold focus:outline-none cursor-pointer ${getStatusColor(log.status)}`}
                  >
                    <option value="Submitted" className="bg-slate-900 text-slate-200">Submitted</option>
                    <option value="Under Review" className="bg-slate-900 text-slate-200">Under Review</option>
                    <option value="Interviewing" className="bg-slate-900 text-slate-200">Interviewing</option>
                    <option value="Accepted" className="bg-slate-900 text-slate-200">Accepted</option>
                  </select>
                </div>

              </div>

              {/* Cover Note Snippet */}
              {log.coverNote && (
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 font-mono line-clamp-2">
                  <span className="text-indigo-400 font-sans font-semibold block mb-0.5">Attached Cover Note:</span>
                  {log.coverNote}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
};
