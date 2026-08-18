import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Briefcase, CheckCircle2, Cpu, FileText, Menu, Repeat, Zap } from 'lucide-react';

import type {
  AiRuntimeConfig,
  ApplicationLog,
  ApplicationStatus,
  FilterState,
  JobPost,
  ResumeProfile,
} from './types/job';
import {
  addApplicationLog,
  availableSources,
  filterJobs,
  getApplicationLogs,
  searchJobs,
  updateApplicationStatus,
} from './services/jobService';
import { getAiConfig, matchJobsBatch } from './services/aiService';
import { getActiveResumeId, getStoredResumes, saveActiveResumeId } from './services/resumeService';

import { type Tab } from './components/Header';
import { JobSearchFilter } from './components/JobSearchFilter';
import { JobCard } from './components/JobCard';
import { ResumeVault } from './components/ResumeVault';
import { ApplicationKitModal } from './components/ApplicationKitModal';
import { AiStatusModal } from './components/AiStatusModal';
import { ApplicationTracker } from './components/ApplicationTracker';
import { AnalyticsOverview } from './components/AnalyticsOverview';
import { LoopsPanel } from './components/LoopsPanel';
import { Sidebar } from './components/Sidebar';
import './App.css';

const EMPTY_FILTER: FilterState = {
  searchQuery: '',
  platform: 'all',
  freshness: 'all',
  experienceYears: '',
  location: '',
  remoteOnly: false,
  minSalary: 0,
};

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('jobs');
  const [filter, setFilter] = useState<FilterState>({ ...EMPTY_FILTER, searchQuery: 'DevOps' });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [jobs, setJobs] = useState<JobPost[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [isScoring, setIsScoring] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const [resumes, setResumes] = useState<ResumeProfile[]>([]);
  const [activeResume, setActiveResume] = useState<ResumeProfile | null>(null);
  const [applicationLogs, setApplicationLogs] = useState<ApplicationLog[]>([]);
  const [aiConfig, setAiConfig] = useState<AiRuntimeConfig | null>(null);

  const [isAiStatusOpen, setIsAiStatusOpen] = useState(false);
  const [openJob, setOpenJob] = useState<JobPost | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadResumes = useCallback(async () => {
    const stored = await getStoredResumes();
    setResumes(stored);

    const savedId = getActiveResumeId();
    const active = stored.find(r => r.id === savedId) ?? stored[0] ?? null;
    setActiveResume(active);
    if (active && active.id !== savedId) saveActiveResumeId(active.id);
  }, []);

  useEffect(() => {
    // Each of these is independent, and one failing must not blank the others.
    void loadResumes().catch(err => setError(err.message));
    void getApplicationLogs().then(setApplicationLogs).catch(() => undefined);
    void getAiConfig().then(setAiConfig).catch(() => setAiConfig(null));
  }, [loadResumes]);

  const filteredJobs = useMemo(() => filterJobs(jobs, filter), [jobs, filter]);
  const sources = useMemo(() => availableSources(jobs), [jobs]);

  /**
   * Search, then score the results against the active resume in one batch
   * request. The cards previously showed a hardcoded 85% read from a field
   * that did not exist on the type.
   */
  const handleFetchJobs = async (useResume = false) => {
    setIsFetching(true);
    setError(null);
    try {
      const results = await searchJobs(filter, useResume);
      setJobs(results);
      setHasSearched(true);

      if (activeResume && results.length > 0) {
        setIsScoring(true);
        try {
          const scores = await matchJobsBatch(activeResume, results);
          setJobs(results.map(job => ({ ...job, match: scores.get(job.id) })));
        } finally {
          setIsScoring(false);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed.');
      setJobs([]);
    } finally {
      setIsFetching(false);
    }
  };

  const handleTrackApplication = async (job: JobPost, coverNote: string, matchScore: number | null) => {
    const logs = await addApplicationLog({
      jobId: job.id,
      status: 'APPLYING',
      resumeUsed: activeResume?.fileName ?? 'None',
      matchScore,
      coverNote,
    });
    setApplicationLogs(logs);
  };

  const handleStatusChange = async (id: string, newStatus: ApplicationStatus) => {
    const previous = applicationLogs;
    // Optimistic, with a rollback — the old code updated locally and silently
    // swallowed a failed sync, so the UI could disagree with the server.
    setApplicationLogs(logs => logs.map(log => (log.id === id ? { ...log, status: newStatus } : log)));
    try {
      setApplicationLogs(await updateApplicationStatus(id, newStatus));
    } catch (err) {
      setApplicationLogs(previous);
      setError(err instanceof Error ? err.message : 'Could not update the status.');
    }
  };

  const isJobTracked = (jobId: string) => applicationLogs.some(log => log.jobId === jobId);

  const handleReset = () => {
    setFilter(EMPTY_FILTER);
    setJobs([]);
    setHasSearched(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col font-sans">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        appliedCount={applicationLogs.length}
        aiConfig={aiConfig}
      />

      <div className="lg:ml-64 flex flex-col min-h-screen">
        {/* Mobile header */}
        <header className="lg:hidden flex items-center justify-between p-4 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Menu className="w-6 h-6 text-gray-600" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900">JobPulse</span>
          </div>
          <div className="w-10" />
        </header>

        <main className="flex-1 px-4 lg:px-8 py-6 lg:py-8 space-y-6">
        {error && (
          <div className="flex items-start justify-between gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
            <span className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              {error}
            </span>
            <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800 font-semibold">
              Dismiss
            </button>
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="space-y-3 z-10">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-3 py-1 text-xs font-bold bg-white/20 border border-white/30 text-white rounded-full flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" />
                    Live aggregation
                  </span>
                  <span
                    className={`px-3 py-1 text-xs font-bold rounded-full flex items-center gap-1.5 border ${
                      aiConfig?.configured
                        ? 'bg-white/20 border-white/30 text-white'
                        : 'bg-white/10 border-white/20 text-white/80'
                    }`}
                  >
                    <Cpu className="w-3.5 h-3.5" />
                    {aiConfig?.configured ? `AI matching via ${aiConfig.providerName}` : 'Keyword matching'}
                  </span>
                </div>

                <h2 className="text-2xl md:text-3xl font-extrabold text-white">
                  Jobs from{' '}
                  <span className="text-white/90">
                    Naukri, LinkedIn, Indeed &amp; More
                  </span>
                </h2>
                <p className="text-xs md:text-sm text-white/90 max-w-2xl">
                  Aggregated, deduplicated across boards, and scored against your resume.
                  You review every application before it is sent — this app never submits on your behalf.
                </p>
              </div>

              <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-4 min-w-[240px] space-y-2 z-10">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-white/80 font-mono uppercase tracking-wider">Active resume</span>
                  {activeResume ? (
                    <span className="text-green-300 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  ) : (
                    <span className="text-amber-300">Missing</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white/20 text-white">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="truncate">
                    <span className="text-xs font-bold text-white block truncate">
                      {activeResume?.fileName ?? 'No resume uploaded'}
                    </span>
                    <span className="text-[11px] text-white/80 block truncate">
                      {activeResume ? `${activeResume.skills.length} skills detected` : 'Scoring unavailable'}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('resumes')}
                  className="w-full py-1.5 rounded-lg bg-white hover:bg-white/90 text-blue-600 text-[11px] font-semibold transition-all"
                >
                  {activeResume ? 'Manage resumes' : 'Upload a resume'}
                </button>
              </div>

              <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/10 rounded-full blur-3xl pointer-events-none" />
            </div>

            <JobSearchFilter
              filter={filter}
              setFilter={setFilter}
              totalMatching={filteredJobs.length}
              availableSources={sources}
              hasResume={Boolean(activeResume)}
              onReset={handleReset}
              onFetch={handleFetchJobs}
              isFetching={isFetching}
            />

            {filteredJobs.length === 0 ? (
              <div className="bg-white border border-gray-200 rounded-2xl p-16 text-center space-y-4">
                <Briefcase className="w-12 h-12 text-gray-400 mx-auto" />
                <h3 className="text-base font-semibold text-gray-900">
                  {!hasSearched
                    ? 'Search to aggregate live jobs'
                    : jobs.length === 0
                      ? 'No jobs came back for that search'
                      : 'No jobs match your current filters'}
                </h3>
                <p className="text-xs text-gray-600 max-w-md mx-auto">
                  {!hasSearched
                    ? 'Enter a role and press Search. Results are fetched live from Naukri, LinkedIn, Indeed, and more.'
                    : jobs.length === 0
                      ? 'Try a broader role, clear the location, or check that the JSearch credentials are set on the server.'
                      : 'Your source or freshness filter is excluding everything that came back.'}
                </p>
                {hasSearched && jobs.length > 0 && (
                  <button
                    onClick={() => setFilter(prev => ({ ...prev, platform: 'all', freshness: 'all' }))}
                    className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredJobs.map(job => (
                  <JobCard
                    key={job.id}
                    job={job}
                    activeResume={activeResume}
                    isApplied={isJobTracked(job.id)}
                    isScoring={isScoring && !job.match}
                    onOpen={setOpenJob}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'loops' && (
          <div className="animate-fadeIn">
            <LoopsPanel
              activeResume={activeResume}
              onOpenJob={job => {
                setOpenJob(job);
              }}
            />
          </div>
        )}

        {activeTab === 'resumes' && (
          <div className="animate-fadeIn">
            <ResumeVault
              resumes={resumes}
              activeResume={activeResume}
              onResumesChanged={loadResumes}
              onActiveChanged={setActiveResume}
            />
          </div>
        )}

        {activeTab === 'tracker' && (
          <div className="animate-fadeIn">
            <ApplicationTracker logs={applicationLogs} onStatusChange={handleStatusChange} />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="animate-fadeIn">
            <AnalyticsOverview />
          </div>
        )}
      </main>

      <footer className="border-t border-gray-200 bg-white py-6 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="flex items-center gap-2">
            <Repeat className="w-3.5 h-3.5" />
            JobPulse — job aggregation, resume matching and application tracking
          </p>
          <p>
            Scoring:{' '}
            <strong className={aiConfig?.configured ? 'text-blue-600' : 'text-gray-400'}>
              {aiConfig?.configured ? aiConfig.model : 'keyword heuristic (no AI key set)'}
            </strong>
          </p>
        </div>
      </footer>
      </div>

      <ApplicationKitModal
        isOpen={Boolean(openJob)}
        job={openJob}
        activeResume={activeResume}
        isApplied={openJob ? isJobTracked(openJob.id) : false}
        onClose={() => setOpenJob(null)}
        onTrackApplication={handleTrackApplication}
      />

      <AiStatusModal
        isOpen={isAiStatusOpen}
        config={aiConfig}
        onClose={() => setIsAiStatusOpen(false)}
      />
    </div>
  );
}
