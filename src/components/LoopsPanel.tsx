import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Clock,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  Trash2,
  X,
} from 'lucide-react';
import type { JobLoop, JobPost, LoopMatch, ResumeProfile } from '../types/job';
import {
  createLoop,
  deleteLoop,
  getLoopMatches,
  listLoops,
  markMatchesSeen,
  runLoop,
  updateLoop,
} from '../services/loopService';
import { MatchBadge } from './MatchBadge';
import { SourceBadge } from './SourceBadge';

/**
 * Loops — standing searches that run on a cadence.
 *
 * The app was request-response: you searched, you looked, you left, and
 * nothing accumulated. A loop keeps searching on a schedule and records what
 * is new since you last looked, which is the difference between a job board
 * viewer and something with a reason to run.
 */

interface LoopsPanelProps {
  activeResume: ResumeProfile | null;
  onOpenJob: (job: JobPost) => void;
}

const CADENCE_OPTIONS = [
  { hours: 6, label: 'Every 6 hours' },
  { hours: 12, label: 'Every 12 hours' },
  { hours: 24, label: 'Daily' },
  { hours: 72, label: 'Every 3 days' },
  { hours: 168, label: 'Weekly' },
];

function formatWhen(iso: string | null): string {
  if (!iso) return 'Never run';
  const diffHours = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${Math.round(diffHours)}h ago`;
  return `${Math.round(diffHours / 24)}d ago`;
}

const CreateLoopForm: React.FC<{
  onCreate: (input: {
    name: string;
    keywords: string[];
    location: string | null;
    remoteOnly: boolean;
    cadenceHours: number;
    minScore: number;
  }) => Promise<void>;
  onCancel: () => void;
}> = ({ onCreate, onCancel }) => {
  const [name, setName] = useState('');
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [cadenceHours, setCadenceHours] = useState(24);
  const [minScore, setMinScore] = useState(50);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedKeywords = keywords
    .split(',')
    .map(k => k.trim())
    .filter(Boolean);

  const submit = async () => {
    setError(null);
    if (!name.trim()) return setError('Give this loop a name.');
    if (parsedKeywords.length === 0) return setError('Add at least one role to search for.');

    setSaving(true);
    try {
      await onCreate({
        name: name.trim(),
        keywords: parsedKeywords,
        location: location.trim() || null,
        remoteOnly,
        cadenceHours,
        minScore,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create this loop.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-cyan-500/30 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-100">New loop</h3>
        <button onClick={onCancel} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Name</span>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Remote DevOps roles"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Roles (comma separated, max 5)
          </span>
          <input
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            placeholder="DevOps Engineer, SRE"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Location (optional)
          </span>
          <input
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Bengaluru"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            How often
          </span>
          <select
            value={cadenceHours}
            onChange={e => setCadenceHours(Number(e.target.value))}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50"
          >
            {CADENCE_OPTIONS.map(option => (
              <option key={option.hours} value={option.hours} className="bg-slate-900">
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
        <label className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Only record matches scoring at least {minScore}%
          </span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-full accent-cyan-500"
          />
        </label>

        <button
          onClick={() => setRemoteOnly(v => !v)}
          className={`px-4 py-2 rounded-xl border text-xs font-semibold transition-all w-fit ${
            remoteOnly
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}
        >
          {remoteOnly ? 'Remote only' : 'Any location type'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-rose-400 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="px-4 py-2 rounded-xl border border-slate-800 text-slate-400 hover:text-white text-xs font-semibold">
          Cancel
        </button>
        <button
          onClick={submit}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Create loop
        </button>
      </div>
    </div>
  );
};

export const LoopsPanel: React.FC<LoopsPanelProps> = ({ activeResume, onOpenJob }) => {
  const [loops, setLoops] = useState<JobLoop[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [matches, setMatches] = useState<LoopMatch[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoops(await listLoops());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load loops.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openLoop = async (loop: JobLoop) => {
    setSelectedId(loop.id);
    setMatches([]);
    try {
      setMatches(await getLoopMatches(loop.id));
      // Opening the loop is what "reviewing" means, so the new badge clears.
      if (loop.newMatches > 0) {
        await markMatchesSeen(loop.id);
        await refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load matches.');
    }
  };

  const handleRun = async (loop: JobLoop) => {
    setRunningId(loop.id);
    setError(null);
    setNotice(null);
    try {
      const result = await runLoop(loop.id);
      if (result.status === 'error') {
        setError(`Run failed: ${result.error}`);
      } else if (result.status === 'skipped') {
        setError(result.error || 'Run skipped.');
      } else {
        setNotice(
          `Fetched ${result.jobsFetched} jobs — ${result.newMatches} new match${
            result.newMatches === 1 ? '' : 'es'
          }, ${result.belowThreshold} below your score threshold.`
        );
      }
      await refresh();
      if (selectedId === loop.id) setMatches(await getLoopMatches(loop.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run this loop.');
    } finally {
      setRunningId(null);
    }
  };

  const handleToggle = async (loop: JobLoop) => {
    try {
      await updateLoop(loop.id, { active: !loop.active });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update this loop.');
    }
  };

  const handleDelete = async (loop: JobLoop) => {
    try {
      await deleteLoop(loop.id);
      if (selectedId === loop.id) {
        setSelectedId(null);
        setMatches([]);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete this loop.');
    }
  };

  const selected = loops.find(loop => loop.id === selectedId) || null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Repeat className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Loops</h2>
            <p className="text-xs text-slate-400">
              Standing searches that keep running on a schedule and collect what is new.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold shadow-lg shadow-cyan-500/20"
        >
          <Plus className="w-4 h-4" />
          New loop
        </button>
      </div>

      {!activeResume && (
        <div className="flex items-start gap-2 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          Loops score jobs against a stored resume. Until you upload one in the Resume Vault,
          runs will be skipped rather than producing scores with nothing behind them.
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {notice && (
        <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-xs text-cyan-300">
          {notice}
        </div>
      )}

      {showForm && (
        <CreateLoopForm
          onCancel={() => setShowForm(false)}
          onCreate={async input => {
            await createLoop(input);
            setShowForm(false);
            await refresh();
          }}
        />
      )}

      {loading ? (
        <div className="text-sm text-slate-500 p-8 text-center">Loading loops…</div>
      ) : loops.length === 0 && !showForm ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <Repeat className="w-8 h-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-bold text-slate-300">No loops yet</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            A loop is a saved search — a set of roles, a location, and how often to re-run it.
            It keeps working between visits so new postings are waiting when you come back.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Loop list */}
          <div className="space-y-3">
            {loops.map(loop => (
              <div
                key={loop.id}
                onClick={() => void openLoop(loop)}
                className={`cursor-pointer bg-slate-900/70 border rounded-2xl p-4 space-y-3 transition-all ${
                  selectedId === loop.id
                    ? 'border-cyan-500/50 shadow-lg shadow-cyan-500/5'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-slate-100 truncate">{loop.name}</h3>
                    <p className="text-[11px] text-slate-500 truncate">{loop.keywords.join(', ')}</p>
                  </div>
                  {loop.newMatches > 0 && (
                    <span className="shrink-0 px-2 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-[10px] font-bold">
                      {loop.newMatches} new
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-500 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {CADENCE_OPTIONS.find(o => o.hours === loop.cadenceHours)?.label ||
                      `Every ${loop.cadenceHours}h`}
                  </span>
                  <span>{loop.totalMatches} total</span>
                  <span>≥{loop.minScore}%</span>
                  {loop.remoteOnly && <span className="text-emerald-500">Remote</span>}
                </div>

                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-[11px] ${
                      loop.lastRunStatus === 'error' ? 'text-rose-400' : 'text-slate-500'
                    }`}
                    title={loop.lastRunError || undefined}
                  >
                    {loop.lastRunStatus === 'error' ? 'Last run failed' : formatWhen(loop.lastRunAt)}
                  </span>

                  <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => void handleRun(loop)}
                      disabled={runningId === loop.id}
                      title="Run now"
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-cyan-300 disabled:opacity-50"
                    >
                      {runningId === loop.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <button
                      onClick={() => void handleToggle(loop)}
                      title={loop.active ? 'Pause this loop' : 'Resume this loop'}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-amber-300"
                    >
                      {loop.active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      onClick={() => void handleDelete(loop)}
                      title="Delete this loop"
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Matches for the selected loop */}
          <div className="lg:col-span-2">
            {!selected ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center text-xs text-slate-500">
                Select a loop to see what it has found.
              </div>
            ) : matches.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center space-y-2">
                <p className="text-sm font-bold text-slate-300">Nothing recorded yet</p>
                <p className="text-xs text-slate-500">
                  {selected.lastRunAt
                    ? `This loop has run, but nothing cleared its ${selected.minScore}% threshold. Lower the threshold or broaden the roles.`
                    : 'This loop has not run yet. Press the refresh icon to run it now.'}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {matches.map(match => (
                  <div
                    key={match.id}
                    className="bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 space-y-3 transition-all"
                  >
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="min-w-0">
                        <h4 className="text-sm font-bold text-slate-100">{match.job.title}</h4>
                        <p className="text-xs text-slate-400">
                          {match.job.company} • {match.job.location}
                        </p>
                      </div>
                      <MatchBadge
                        match={{
                          score: match.score,
                          matchedSkills: match.matchedSkills,
                          missingSkills: match.missingSkills,
                          summary: '',
                          recommendations: [],
                          method: match.scoreMethod,
                          confidence: 'medium',
                        }}
                      />
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      <SourceBadge source={match.job.platform} allSources={match.job.sources} />
                      <span className="text-[11px] text-slate-500">{match.job.postedTime}</span>
                    </div>

                    {match.matchedSkills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {match.matchedSkills.slice(0, 6).map(skill => (
                          <span key={skill} className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 font-mono">
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}

                    <button
                      onClick={() => onOpenJob(match.job)}
                      className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
                    >
                      Prepare application
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
