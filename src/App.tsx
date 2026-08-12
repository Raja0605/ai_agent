import { useState, useMemo, useEffect } from 'react';
import { 
  Briefcase, 
  Send, 
  Sparkles, 
  Zap, 
  FileText, 
  Layers, 
  CheckCircle2, 
  Bot,
  Plus
} from 'lucide-react';

import type { 
  JobPost, 
  FilterState, 
  ResumeProfile, 
  ApplicationLog, 
  AiConfigState 
} from './types/job';
import { INITIAL_JOBS } from './data/mockJobs';
import { filterJobs, getApplicationLogs, addApplicationLog } from './services/jobService';
import { getStoredResumes, getActiveResume } from './services/resumeService';
import { getSavedAiConfig } from './config/aiConfig';

import { Header } from './components/Header';
import { JobSearchFilter } from './components/JobSearchFilter';
import { JobCard } from './components/JobCard';
import { ResumeModal } from './components/ResumeModal';
import { AutoApplyModal } from './components/AutoApplyModal';
import { AiSettingsModal } from './components/AiSettingsModal';
import { ApplicationTracker } from './components/ApplicationTracker';
import { AnalyticsOverview } from './components/AnalyticsOverview';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState<'jobs' | 'resumes' | 'tracker' | 'analytics'>('jobs');
  
  // Filter State
  const [filter, setFilter] = useState<FilterState>({
    searchQuery: 'DevOps',
    platform: 'all',
    freshness: 'all',
    experienceLevel: 'all',
    remoteOnly: false,
    minSalary: 0
  });

  // Stored Resumes & Active Default Resume
  const [resumes, setResumes] = useState<ResumeProfile[]>([]);
  const [activeResume, setActiveResume] = useState<ResumeProfile>(() => getActiveResume());
  
  // Application Logs
  const [applicationLogs, setApplicationLogs] = useState<ApplicationLog[]>([]);

  // AI Settings Config
  const [aiConfig, setAiConfig] = useState<AiConfigState>(() => getSavedAiConfig());

  // Modals
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [isAiSettingsOpen, setIsAiSettingsOpen] = useState(false);
  const [applyModalJob, setApplyModalJob] = useState<JobPost | null>(null);

  // Load initial data
  useEffect(() => {
    const storedRes = getStoredResumes();
    setResumes(storedRes);
    const active = getActiveResume();
    setActiveResume(active);

    const logs = getApplicationLogs();
    setApplicationLogs(logs);
  }, []);

  // Filtered jobs list
  const filteredJobs = useMemo(() => {
    return filterJobs(INITIAL_JOBS, filter);
  }, [filter]);

  // Handle auto-apply trigger
  const handleApplyClick = (job: JobPost) => {
    setApplyModalJob(job);
  };

  // Confirm application modal submission
  const handleConfirmApply = (job: JobPost, coverNote: string, atsScore: number) => {
    const newLogs = addApplicationLog({
      jobId: job.id,
      jobTitle: job.title,
      company: job.company,
      platform: job.platform,
      appliedAt: 'Today at ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'Submitted',
      resumeUsed: activeResume.fileName,
      atsScore,
      coverNote
    });

    setApplicationLogs(newLogs);
    setApplyModalJob(null);
  };

  // Update Status in Application History
  const handleStatusChange = (id: string, newStatus: ApplicationLog['status']) => {
    const updated = applicationLogs.map(log => 
      log.id === id ? { ...log, status: newStatus } : log
    );
    setApplicationLogs(updated);
    localStorage.setItem('job_pulse_application_logs', JSON.stringify(updated));
  };

  // Update Resumes List
  const handleUpdateResumes = (updated: ResumeProfile[], active: ResumeProfile) => {
    setResumes(updated);
    setActiveResume(active);
  };

  const isJobApplied = (jobId: string) => {
    return applicationLogs.some(log => log.jobId === jobId);
  };

  const handleResetFilters = () => {
    setFilter({
      searchQuery: '',
      platform: 'all',
      freshness: 'all',
      experienceLevel: 'all',
      remoteOnly: false,
      minSalary: 0
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      
      {/* Top Header & Navigation */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeResume={activeResume}
        appliedCount={applicationLogs.length}
        totalJobsCount={INITIAL_JOBS.length}
        onOpenResumeModal={() => setIsResumeModalOpen(true)}
        onOpenAiSettings={() => setIsAiSettingsOpen(true)}
        aiConfig={aiConfig}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-8 space-y-8">
        
        {/* TAB 1: JOBS SEARCH & AUTO-APPLY GRID */}
        {activeTab === 'jobs' && (
          <div className="space-y-8 animate-fadeIn">
            
            {/* Hero Banner / Active Resume Ribbon */}
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-cyan-950/80 via-slate-900 to-indigo-950/80 border border-slate-800 p-6 md:p-8 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="space-y-2 text-center md:text-left z-10">
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <span className="px-3 py-1 text-xs font-bold bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 rounded-full flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    Multi-Platform Job Pulse
                  </span>
                  <span className="px-3 py-1 text-xs font-bold bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 rounded-full flex items-center gap-1.5">
                    <Bot className="w-3.5 h-3.5 text-indigo-400" />
                    {aiConfig.googleModel}
                  </span>
                </div>
                <h2 className="text-2xl md:text-3xl font-extrabold text-white">
                  Fetch Latest Jobs from <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">Naukri & Indeed</span>
                </h2>
                <p className="text-xs md:text-sm text-slate-300 max-w-2xl">
                  Filter by posting freshness (<strong className="text-cyan-400">Just now</strong>, 1-3 days ago) and auto-apply using your stored resume profile with 1-click execution.
                </p>
              </div>

              {/* Stored Resume Quick Card */}
              <div className="bg-slate-950/90 border border-cyan-500/40 rounded-2xl p-4 min-w-[260px] shadow-xl space-y-2 z-10">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-cyan-400 font-mono font-bold uppercase tracking-wider">Stored Web Resume</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Ready
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="truncate">
                    <span className="text-xs font-bold text-slate-100 block truncate">{activeResume.fileName}</span>
                    <span className="text-[11px] text-slate-400 block truncate">{activeResume.fullName}</span>
                  </div>
                </div>
                <button
                  onClick={() => setIsResumeModalOpen(true)}
                  className="w-full py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-cyan-300 font-semibold transition-all flex items-center justify-center gap-1"
                >
                  Manage Stored Resume
                </button>
              </div>

              {/* Decorative Glow */}
              <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
            </div>

            {/* Filter Toolbar */}
            <JobSearchFilter
              filter={filter}
              setFilter={setFilter}
              totalMatching={filteredJobs.length}
              onReset={handleResetFilters}
            />

            {/* Job Grid */}
            {filteredJobs.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-16 text-center space-y-4">
                <Briefcase className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-base font-bold text-slate-200">No Jobs Match Your Current Filter</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Try clearing the freshness filter or searching for popular roles like <strong className="text-cyan-400">DevOps</strong>, <strong className="text-cyan-400">Kubernetes</strong>, or <strong className="text-cyan-400">React</strong>.
                </p>
                <button
                  onClick={handleResetFilters}
                  className="px-5 py-2.5 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-bold hover:bg-cyan-500/30 transition-all"
                >
                  Reset All Filters
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredJobs.map(job => (
                  <JobCard
                    key={job.id}
                    job={job}
                    activeResume={activeResume}
                    isApplied={isJobApplied(job.id)}
                    onApplyClick={handleApplyClick}
                  />
                ))}
              </div>
            )}

          </div>
        )}

        {/* TAB 2: RESUME VAULT */}
        {activeTab === 'resumes' && (
          <div className="animate-fadeIn">
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-8 space-y-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
                <div>
                  <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-cyan-400" />
                    Web Resume Vault & ATS Optimizer
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Upload and select stored resumes to automatically dispatch with 1-click on Naukri & Indeed
                  </p>
                </div>

                <button
                  onClick={() => setIsResumeModalOpen(true)}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold shadow-lg shadow-cyan-500/20 hover:scale-105 transition-all"
                >
                  <Plus className="w-4 h-4" />
                  Upload New Resume Profile
                </button>
              </div>

              {/* Resume Profiles Display */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {resumes.map(resume => {
                  const isActive = resume.id === activeResume.id;
                  return (
                    <div
                      key={resume.id}
                      className={`p-6 rounded-2xl border transition-all space-y-4 ${
                        isActive
                          ? 'bg-slate-950/90 border-cyan-500/50 shadow-xl shadow-cyan-500/10'
                          : 'bg-slate-950/40 border-slate-800'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-slate-100">{resume.fileName}</h3>
                            {isActive && (
                              <span className="px-2 py-0.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded-full">
                                DEFAULT ACTIVE
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400">{resume.fullName} • {resume.targetRole}</p>
                        </div>
                      </div>

                      <p className="text-xs text-slate-400 line-clamp-3 bg-slate-900 p-3 rounded-xl border border-slate-800">
                        {resume.summary}
                      </p>

                      <div className="space-y-1.5">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Stored Skill Profile:</span>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {resume.skills.map(s => (
                            <span key={s} className="text-[11px] px-2.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          </div>
        )}

        {/* TAB 3: APPLICATION TRACKER */}
        {activeTab === 'tracker' && (
          <div className="animate-fadeIn">
            <ApplicationTracker
              logs={applicationLogs}
              onStatusChange={handleStatusChange}
            />
          </div>
        )}

        {/* TAB 4: ANALYTICS OVERVIEW */}
        {activeTab === 'analytics' && (
          <div className="animate-fadeIn">
            <AnalyticsOverview
              jobs={INITIAL_JOBS}
              logs={applicationLogs}
              activeResume={activeResume}
            />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 JobPulse AutoApply • Multi-Platform Job Fetcher & Resume Dispatcher</p>
          <div className="flex items-center gap-4 text-slate-400">
            <span>Model: <strong className="text-indigo-400">{aiConfig.googleModel}</strong></span>
            <span>Active Resume: <strong className="text-cyan-400">{activeResume.fileName}</strong></span>
          </div>
        </div>
      </footer>

      {/* MODALS */}
      <ResumeModal
        isOpen={isResumeModalOpen}
        onClose={() => setIsResumeModalOpen(false)}
        resumes={resumes}
        activeResume={activeResume}
        onUpdateResumes={handleUpdateResumes}
      />

      <AutoApplyModal
        isOpen={!!applyModalJob}
        job={applyModalJob}
        activeResume={activeResume}
        aiConfig={aiConfig}
        onClose={() => setApplyModalJob(null)}
        onConfirmApply={handleConfirmApply}
      />

      <AiSettingsModal
        isOpen={isAiSettingsOpen}
        onClose={() => setIsAiSettingsOpen(false)}
        config={aiConfig}
        onSave={setAiConfig}
      />

    </div>
  );
}
