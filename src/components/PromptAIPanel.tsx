import { useMemo, useState } from 'react';
import { Sparkles, Search } from 'lucide-react';
import type { JobPost, ResumeProfile } from '../types/job';
import { JobCard } from './JobCard';
import { sourceLabel } from './SourceBadge';
import { promptAiSearch, type PromptAISourceStatus } from '../services/promptAiService';

type ResultFilter = 'best' | 'all' | string;

export function PromptAIPanel({
  resumes,
  selectedResume,
  onSelectResume,
  isApplied,
  onOpenJob,
}: {
  resumes: ResumeProfile[];
  selectedResume: ResumeProfile | null;
  onSelectResume: (resume: ResumeProfile) => void;
  isApplied: (jobId: string) => boolean;
  onOpenJob: (job: JobPost) => void;
}) {
  const [prompt, setPrompt] = useState(
    'Find DevOps Engineer jobs in Chennai with Kubernetes and Docker experience, preferably remote or hybrid.',
  );
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [jobs, setJobs] = useState<JobPost[]>([]);
  const [sources, setSources] = useState<Record<string, PromptAISourceStatus>>({});
  const [filter, setFilter] = useState<ResultFilter>('best');
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);
  const [interpreted, setInterpreted] = useState<string>('');

  const visible = useMemo(() => {
    if (filter === 'best') return jobs.filter(job => (job.match?.score ?? 0) >= 60);
    if (filter === 'all') return jobs;
    return jobs.filter(job => job.platform === filter || job.sources.includes(filter));
  }, [filter, jobs]);

  const sourceKeys = useMemo(() => {
    const seen = new Set<string>();
    jobs.forEach(job => job.sources.forEach(source => seen.add(source)));
    return Array.from(seen);
  }, [jobs]);

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim() || !selectedResume) return;
    setBusy(true);
    setError('');
    setProgress([]);
    setJobs([]);
    setSources({});
    setTotal(0);
    setInterpreted('');
    try {
      const data = await promptAiSearch(prompt.trim(), selectedResume.id, message => {
        setProgress(current => (current.includes(message) ? current : [...current, message]));
      });
      setJobs(data.results);
      setSources(data.source_status);
      setProgress(data.progress);
      setTotal(data.total);
      setFilter('best');
      const bits = [
        data.interpreted.keywords.join(', '),
        data.interpreted.locations.join(', '),
        data.interpreted.remote ? 'remote' : '',
        data.interpreted.skills.join(', '),
      ].filter(Boolean);
      setInterpreted(bits.join(' · '));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prompt AI search failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <p className="text-sm font-semibold text-blue-600">Natural-language matching</p>
        <h2 className="text-2xl font-bold">Prompt AI</h2>
        <p className="text-sm text-gray-600">
          Describe the job you want. Prompt AI uses a resume already stored in JobPulse, searches the
          existing job sources, then ranks the results with the existing match scorer.
        </p>
      </div>

      <form onSubmit={search} className="rounded-2xl border border-gray-200 bg-white p-5 md:p-6 space-y-5 shadow-sm">
        <label className="block text-sm font-semibold text-gray-900">
          What job are you looking for?
          <textarea
            value={prompt}
            onChange={event => setPrompt(event.target.value)}
            rows={4}
            className="mt-2 w-full rounded-xl border border-gray-200 p-3 text-sm text-gray-800 focus:border-blue-400 focus:outline-none"
            placeholder="Find DevOps Engineer jobs in Chennai with Kubernetes and Docker experience, preferably remote or hybrid."
          />
        </label>

        <label className="block text-sm font-semibold text-gray-900">
          Resume
          <select
            value={selectedResume?.id ?? ''}
            onChange={event => {
              const next = resumes.find(resume => resume.id === event.target.value);
              if (next) onSelectResume(next);
            }}
            className="mt-2 w-full rounded-xl border border-gray-200 p-2.5 text-sm"
            disabled={resumes.length === 0}
          >
            {resumes.length === 0 && <option value="">No resumes uploaded</option>}
            {resumes.map(resume => (
              <option key={resume.id} value={resume.id}>
                {resume.fileName}
              </option>
            ))}
          </select>
        </label>

        {resumes.length === 0 && (
          <p className="text-sm text-amber-700">
            Upload a resume in the Resumes tab first. Prompt AI does not create a separate resume store.
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !selectedResume || !prompt.trim()}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          <Search className="mr-2 inline h-4 w-4" />
          {busy ? 'Finding matching jobs…' : 'Find Matching Jobs'}
        </button>
      </form>

      {progress.length > 0 && (
        <div className="rounded-xl border bg-white p-4 text-sm text-gray-700 space-y-1">
          {progress.map(step => (
            <p key={step}>{step}</p>
          ))}
        </div>
      )}

      {Object.keys(sources).length > 0 && (
        <div className="rounded-xl border bg-white p-4 text-sm space-y-1">
          {Object.entries(sources).map(([source, state]) => (
            <p key={source} className={state.status === 'failed' ? 'text-amber-700' : 'text-gray-700'}>
              {sourceLabel(source)} {state.status === 'success' ? 'SUCCESS' : 'FAILED'}
              {state.status === 'failed' ? ` — ${state.message || `${sourceLabel(source)} temporarily unavailable.`}` : ` ${state.count}`}
            </p>
          ))}
        </div>
      )}

      {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {interpreted && <p className="text-xs text-gray-500">Interpreted as: {interpreted}</p>}

      {total > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <b className="mr-2">{total} jobs found</b>
            <button type="button" onClick={() => setFilter('best')} className="rounded-lg border px-3 py-1.5 text-sm">
              Best Matches
            </button>
            <button type="button" onClick={() => setFilter('all')} className="rounded-lg border px-3 py-1.5 text-sm">
              All
            </button>
            {sourceKeys.map(source => (
              <button
                key={source}
                type="button"
                onClick={() => setFilter(source)}
                className="rounded-lg border px-3 py-1.5 text-sm"
              >
                {sourceLabel(source)}
              </button>
            ))}
          </div>
          {visible.length === 0 ? (
            <p className="rounded-xl border bg-white p-8 text-center text-sm text-gray-600">
              No jobs in this view. Try All Results.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {visible.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  activeResume={selectedResume}
                  isApplied={isApplied(job.id)}
                  onOpen={onOpenJob}
                  showMatchDetails
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!busy && total === 0 && progress.length > 0 && !error && (
        <p className="rounded-xl border bg-white p-8 text-center text-sm text-gray-600">
          No matching jobs were returned from the sources that succeeded.
        </p>
      )}

      <p className="text-xs text-gray-500">
        <Sparkles className="mr-1 inline h-3 w-3" />
        Prompt AI interprets your sentence locally, then reuses Jobs, AI Server, and Job Spy search. It does not invent jobs or resume skills.
      </p>
    </div>
  );
}
