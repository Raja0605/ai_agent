import { useEffect, useMemo, useState } from 'react';
import { Radar, RefreshCw, Search, Wifi } from 'lucide-react';
import type { JobPost } from '../types/job';
import { JobCard } from './JobCard';
import { sourceLabel } from './SourceBadge';
import {
  jobspySearch,
  jobspyTest,
  jobspyTools,
  type JobSpyPortalStatus,
} from '../services/jobspyService';

const BOARD_LABELS: Record<string, string> = {
  indeed: 'Indeed',
  linkedin: 'LinkedIn',
  naukri: 'Naukri',
  glassdoor: 'Glassdoor',
  google: 'Google Jobs',
  zip_recruiter: 'ZipRecruiter',
  bayt: 'Bayt',
  bdjobs: 'BDJobs',
};

const DEFAULT_BOARDS = ['indeed', 'linkedin', 'naukri', 'glassdoor', 'google'];

function boardLabel(board: string) {
  return BOARD_LABELS[board] || sourceLabel(board);
}

export function JobSpyPanel({ onOpenJob }: { onOpenJob: (job: JobPost) => void }) {
  const [boards, setBoards] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [connection, setConnection] = useState<'Connected' | 'Disconnected' | 'Error' | 'Searching'>('Disconnected');
  const [host, setHost] = useState('jobspy_mcp');
  const [port, setPort] = useState(8500);
  const [term, setTerm] = useState('DevOps Engineer');
  const [location, setLocation] = useState('Chennai');
  const [country, setCountry] = useState('India');
  const [remote, setRemote] = useState('any');
  const [jobType, setJobType] = useState('any');
  const [posted, setPosted] = useState('any');
  const [limit, setLimit] = useState(20);
  const [jobs, setJobs] = useState<JobPost[]>([]);
  const [sources, setSources] = useState<Record<string, number>>({});
  const [portals, setPortals] = useState<Record<string, JobSpyPortalStatus>>({});
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState('all');
  const [progress, setProgress] = useState('');
  const [message, setMessage] = useState('');

  const loadTools = async () => {
    try {
      const data = await jobspyTools();
      const sites = data.sites || [];
      setBoards(sites);
      setSelected(current => {
        const next = current.filter(site => sites.includes(site));
        if (next.length) return next;
        return sites.filter(site => DEFAULT_BOARDS.includes(site));
      });
      setHost(data.host || 'jobspy_mcp');
      setPort(data.port || 8500);
      setConnection(data.status === 'connected' ? 'Connected' : 'Disconnected');
      setMessage('');
    } catch {
      setBoards([]);
      setConnection('Disconnected');
    }
  };

  useEffect(() => {
    void loadTools();
  }, []);

  const visible = useMemo(
    () => (active === 'all' ? jobs : jobs.filter(job => job.platform === `jobspy:${active}` || job.sources.includes(`jobspy:${active}`))),
    [active, jobs],
  );

  const toggle = (board: string) => {
    setSelected(current => (current.includes(board) ? current.filter(item => item !== board) : [...current, board]));
  };

  const testConnection = async () => {
    try {
      const data = await jobspyTest();
      setConnection(data.status === 'connected' ? 'Connected' : 'Error');
      setHost(data.host || host);
      setPort(data.port || port);
      setBoards(data.sites || boards);
      setMessage(data.status === 'connected' ? 'Connection test succeeded.' : 'Job Spy MCP is disconnected.');
    } catch {
      setConnection('Error');
      setMessage('Job Spy MCP is disconnected.');
    }
  };

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!term.trim() || !selected.length) return;
    setBusy(true);
    setConnection('Searching');
    setProgress(selected.map(board => `Searching ${boardLabel(board)}...`).join('  '));
    setMessage('');
    try {
      const data = await jobspySearch({
        search_term: term,
        location,
        site_name: selected,
        results_wanted: limit,
        job_type: jobType === 'any' ? null : jobType,
        is_remote: remote === 'any' ? null : remote === 'true',
        hours_old: posted === 'any' ? null : Number(posted),
        country_indeed: country || 'india',
      });
      setJobs(data.results);
      setSources(data.sources);
      setPortals(data.portal_status);
      setActive('all');
      setConnection('Connected');
      const lines = Object.entries(data.portal_status).map(([site, state]) => {
        if (state.status === 'success') return `${boardLabel(site)}: ${state.count} jobs`;
        if (state.status === 'no_results') return `${boardLabel(site)}: 0 (no results for this query)`;
        if (state.status === 'unavailable') {
          return `${boardLabel(site)}: unavailable — ${state.message || 'blocked by provider'}`;
        }
        return `${boardLabel(site)}: temporarily unavailable${state.message ? ` — ${state.message}` : ''}`;
      });
      const unique = data.results.length;
      const raw = data.raw_total ?? data.total;
      const totalLine =
        raw != null && raw !== unique
          ? `Unique jobs: ${unique} (raw portal hits: ${raw}; ${raw - unique} cross-board duplicate${raw - unique === 1 ? '' : 's'} merged)`
          : `Total: ${unique}`;
      setProgress(`Search completed\n${lines.join('\n')}\n${totalLine}`);
    } catch {
      setConnection('Error');
      setProgress('');
      setMessage('Job Spy is temporarily unavailable');
    } finally {
      setBusy(false);
    }
  };

  const statusColor =
    connection === 'Connected' ? 'text-emerald-600' : connection === 'Searching' ? 'text-blue-600' : 'text-amber-600';

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-blue-600">Multi-board MCP search</p>
        <h2 className="text-2xl font-bold">Job Spy</h2>
        <p className="text-sm text-gray-600">
          Search supported boards through the separate JobSpy MCP service. This is not the AI Server.
        </p>
      </div>

      <div className="rounded-xl border bg-white p-4 text-sm space-y-3">
        <h3 className="font-semibold">Job Spy Settings</h3>
        <p>
          <Wifi className={`mr-2 inline h-4 w-4 ${statusColor}`} />
          MCP Server: {connection}
        </p>
        <p>Server: {host}</p>
        <p>Port: {port}</p>
        <p>
          Status: <span className={statusColor}>● {connection}</span>
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void testConnection()} className="rounded border px-3 py-1.5 text-sm">
            Test Connection
          </button>
          <button type="button" onClick={() => void loadTools()} className="rounded border px-3 py-1.5 text-sm">
            <RefreshCw className="mr-1 inline h-3 w-3" />
            Refresh Tools
          </button>
        </div>
      </div>

      {message && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{message}</p>}

      <form onSubmit={search} className="rounded-xl border bg-white p-5 shadow-sm">
        <h3 className="font-semibold">Search Jobs</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium">
            Keywords
            <input value={term} onChange={event => setTerm(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5" />
          </label>
          <label className="text-sm font-medium">
            Location
            <input value={location} onChange={event => setLocation(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5" />
          </label>
          <label className="text-sm font-medium">
            Country
            <input value={country} onChange={event => setCountry(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5" />
          </label>
          <label className="text-sm font-medium">
            Remote
            <select value={remote} onChange={event => setRemote(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5">
              <option value="any">Any</option>
              <option value="true">Remote only</option>
              <option value="false">On-site / Hybrid</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Job Type
            <select value={jobType} onChange={event => setJobType(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5">
              <option value="any">Any</option>
              <option value="fulltime">Full-time</option>
              <option value="parttime">Part-time</option>
              <option value="contract">Contract</option>
              <option value="internship">Internship</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Posted Within
            <select value={posted} onChange={event => setPosted(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5">
              <option value="any">Any</option>
              <option value="24">Last 24 hours</option>
              <option value="72">Last 3 days</option>
              <option value="168">Last 7 days</option>
              <option value="720">Last 30 days</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Results per portal
            <select value={limit} onChange={event => setLimit(Number(event.target.value))} className="mt-1 w-full rounded-lg border p-2.5">
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
        <fieldset className="mt-5">
          <legend className="text-sm font-semibold">Job Boards</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {boards.length === 0 && <p className="text-sm text-gray-500">Connect Job Spy MCP to load supported boards.</p>}
            {boards.map(board => (
              <label key={board} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={selected.includes(board)} onChange={() => toggle(board)} />
                {boardLabel(board)}
              </label>
            ))}
          </div>
        </fieldset>
        <button disabled={busy || !selected.length} className="mt-5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
          <Search className="mr-2 inline h-4 w-4" />
          {busy ? 'Searching…' : 'Search Jobs'}
        </button>
      </form>

      {progress && (
        <pre className="whitespace-pre-wrap rounded-xl border bg-white p-4 text-sm text-gray-700">{progress}</pre>
      )}

      {Object.keys(portals).length > 0 && (
        <div className="rounded-xl border bg-white p-4 text-sm space-y-1">
          <p className="font-semibold mb-2 text-gray-800">Portal Status</p>
          {Object.entries(portals).map(([site, state]) => {
            const isSuccess = state.status === 'success';
            const isUnavailable = state.status === 'unavailable';
            const isNoResults = state.status === 'no_results';
            const colorClass = isSuccess
              ? 'text-emerald-700'
              : isNoResults
                ? 'text-gray-500'
                : isUnavailable
                  ? 'text-amber-700'
                  : 'text-red-700';
            const badge = isSuccess
              ? `✅ SUCCESS — ${state.count} jobs`
              : isNoResults
                ? '⬜ NO RESULTS'
                : isUnavailable
                  ? '🚫 UNAVAILABLE'
                  : '❌ FAILED';
            return (
              <p key={site} className={colorClass}>
                <span className="font-medium">{boardLabel(site)}:</span> {badge}
                {state.message && !isSuccess ? ` — ${state.message}` : ''}
              </p>
            );
          })}
        </div>
      )}

      {jobs.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <b className="mr-2">{jobs.length} jobs found</b>
            <button type="button" onClick={() => setActive('all')} className="rounded border px-3 py-1 text-sm">
              All ({jobs.length})
            </button>
            {Object.entries(sources)
              .filter(([source, count]) => source.startsWith('jobspy:') && count > 0)
              .map(([source, count]) => {
              const key = source.replace('jobspy:', '');
              return (
                <button key={source} type="button" onClick={() => setActive(key)} className="rounded border px-3 py-1 text-sm">
                  {boardLabel(key)} ({count})
                </button>
              );
            })}
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visible.map(job => (
              <JobCard key={job.id} job={job} activeResume={null} isApplied={false} onOpen={onOpenJob} />
            ))}
          </div>
        </>
      )}

      <p className="text-xs text-gray-500">
        <Radar className="mr-1 inline h-3 w-3" />
        Board availability and rate limits vary. Job Spy does not use proxy rotation, CAPTCHA bypass, or account credentials.
      </p>
    </div>
  );
}
