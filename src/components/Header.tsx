import React from 'react';
import { BarChart3, Bot, Briefcase, Cpu, FileText, Layers, Repeat, Send, Sparkles } from 'lucide-react';
import type { AiRuntimeConfig, ResumeProfile } from '../types/job';

export type Tab = 'jobs' | 'loops' | 'resumes' | 'tracker' | 'analytics';

interface HeaderProps {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
  activeResume: ResumeProfile | null;
  appliedCount: number;
  totalJobsCount: number;
  newLoopMatches: number;
  aiConfig: AiRuntimeConfig | null;
  onOpenResumeModal: () => void;
  onOpenAiStatus: () => void;
}

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'jobs', label: 'Jobs', icon: <Layers className="w-3.5 h-3.5" /> },
  { key: 'loops', label: 'Loops', icon: <Repeat className="w-3.5 h-3.5" /> },
  { key: 'resumes', label: 'Resumes', icon: <FileText className="w-3.5 h-3.5" /> },
  { key: 'tracker', label: 'Tracker', icon: <Send className="w-3.5 h-3.5" /> },
  { key: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-3.5 h-3.5" /> },
];

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  activeResume,
  appliedCount,
  totalJobsCount,
  newLoopMatches,
  aiConfig,
  onOpenResumeModal,
  onOpenAiStatus,
}) => {
  const counts: Partial<Record<Tab, number>> = {
    jobs: totalJobsCount,
    loops: newLoopMatches,
    tracker: appliedCount,
  };

  return (
    <header className="sticky top-0 z-40 px-4 lg:px-8 py-3 backdrop-blur-xl border-b border-slate-800/80 bg-slate-950/80">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-4">

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 p-[2px] shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-cyan-400 bg-clip-text text-transparent">
              JobPulse
            </h1>
            {/* Describes what the app does, not what it once claimed to do:
                it aggregates Remotive and Adzuna, scores jobs against your
                resume, and tracks what you applied to. It does not dispatch
                applications to Naukri or Indeed. */}
            <p className="text-xs text-slate-400">
              Aggregate, match and track — you stay in control of every submission
            </p>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800 flex-wrap justify-center">
          {TABS.map(tab => {
            const count = counts[tab.key];
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === tab.key
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {tab.icon}
                {tab.label}
                {count !== undefined && count > 0 && (
                  <span
                    className={`px-1.5 rounded-full text-[10px] font-bold ${
                      activeTab === tab.key ? 'bg-white/20' : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenResumeModal}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/40 text-xs text-slate-200 transition-all"
            title="Manage stored resumes"
          >
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <div className="text-left hidden sm:block max-w-[140px] truncate">
              <span className="text-[10px] text-slate-500 block uppercase tracking-wider">Resume</span>
              <span className="font-semibold text-slate-100 truncate block">
                {activeResume ? activeResume.fileName : 'None uploaded'}
              </span>
            </div>
          </button>

          {/* Reports the AI configuration the server actually has, replacing a
              badge that displayed an editable client-side model name with no
              connection to what the backend called. */}
          <button
            onClick={onOpenAiStatus}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/90 border text-xs transition-all ${
              aiConfig?.configured
                ? 'border-indigo-500/30 text-indigo-300'
                : 'border-slate-800 text-slate-400'
            }`}
            title={
              aiConfig?.configured
                ? `AI evaluation active via ${aiConfig.providerName}`
                : 'No AI key configured — scores are keyword-based'
            }
          >
            {aiConfig?.configured ? (
              <Bot className="w-3.5 h-3.5 text-indigo-400" />
            ) : (
              <Cpu className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span className="hidden lg:inline text-[11px] font-mono">
              {aiConfig ? (aiConfig.configured ? aiConfig.model : 'No AI key') : '…'}
            </span>
            {aiConfig?.configured && <Sparkles className="w-3 h-3 text-indigo-400" />}
          </button>
        </div>
      </div>
    </header>
  );
};
