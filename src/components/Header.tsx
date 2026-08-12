import React from 'react';
import { 
  Briefcase, 
  FileText, 
  Sparkles, 
  Send, 
  Layers, 
  CheckCircle2,
  SlidersHorizontal,
  Bot
} from 'lucide-react';
import type { AiConfigState, ResumeProfile } from '../types/job';

interface HeaderProps {
  activeTab: 'jobs' | 'resumes' | 'tracker' | 'analytics';
  setActiveTab: (tab: 'jobs' | 'resumes' | 'tracker' | 'analytics') => void;
  activeResume: ResumeProfile;
  appliedCount: number;
  totalJobsCount: number;
  onOpenResumeModal: () => void;
  onOpenAiSettings: () => void;
  aiConfig: AiConfigState;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  activeResume,
  appliedCount,
  totalJobsCount,
  onOpenResumeModal,
  onOpenAiSettings,
  aiConfig
}) => {
  return (
    <header className="header-glass sticky top-0 z-40 px-4 lg:px-8 py-3 backdrop-blur-xl border-b border-slate-800/80 bg-slate-950/80">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand Logo & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 p-[2px] shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-cyan-400 bg-clip-text text-transparent">
                JobPulse<span className="text-cyan-400">.AutoApply</span>
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                Live Feeds
              </span>
            </div>
            <p className="text-xs text-slate-400">Naukri & Indeed Multi-Platform Job Fetcher & Auto Resume Dispatcher</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('jobs')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'jobs'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Jobs ({totalJobsCount})
          </button>

          <button
            onClick={() => setActiveTab('resumes')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'resumes'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Resume Vault
          </button>

          <button
            onClick={() => setActiveTab('tracker')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'tracker'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            Applied ({appliedCount})
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'analytics'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Analytics
          </button>
        </nav>

        {/* Right Status Actions: Resume Selector & AI Settings */}
        <div className="flex items-center gap-2">
          {/* Active Stored Resume Pill */}
          <button
            onClick={onOpenResumeModal}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-cyan-500/30 text-xs text-slate-200 hover:border-cyan-400 transition-all group"
            title="Click to manage or change active resume"
          >
            <FileText className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
            <div className="text-left hidden sm:block max-w-[140px] truncate">
              <span className="text-[10px] text-cyan-400 block font-mono uppercase tracking-wider">Active Resume</span>
              <span className="font-semibold text-slate-100 truncate block">{activeResume.fileName}</span>
            </div>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 ml-1" />
          </button>

          {/* AI Provider Button */}
          <button
            onClick={onOpenAiSettings}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 transition-all"
            title="Configure Gemini 3.1 Pro / OpenAI models"
          >
            <Bot className="w-3.5 h-3.5 text-indigo-400 animate-spin-slow" />
            <span className="hidden lg:inline text-[11px] font-mono text-indigo-300">{aiConfig.googleModel}</span>
            <SlidersHorizontal className="w-3 h-3 text-slate-400" />
          </button>
        </div>

      </div>
    </header>
  );
};
