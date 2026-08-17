import React, { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, Clock, Database, Send, TrendingUp } from 'lucide-react';
import type { AnalyticsData, RatePerformance } from '../types/job';
import { getAnalytics } from '../services/analyticsService';
import { sourceLabel } from './SourceBadge';

/**
 * Analytics computed from tracked data.
 *
 * What this replaces: bars counting Naukri/Indeed/LinkedIn/Foundit jobs that
 * the backend never fetched (so every bar read zero), a literal `founditCount
 * + 2` added to one of them, and an "Avg ATS Match Score" that displayed a
 * hardcoded 92% whenever there were no applications to average.
 *
 * The rule here is that a metric with no data behind it says so, rather than
 * rendering a confident-looking number.
 */

const NO_DATA = '—';

function formatRate(value: number | null): string {
  return value === null ? NO_DATA : `${value}%`;
}

const StatCard: React.FC<{
  label: string;
  value: string;
  hint: string;
  icon: React.ReactNode;
  tone?: string;
}> = ({ label, value, hint, icon, tone = 'text-white' }) => (
  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-2">
    <div className="flex items-center justify-between text-xs text-slate-400">
      <span className="font-semibold uppercase tracking-wider">{label}</span>
      {icon}
    </div>
    <div className={`text-3xl font-extrabold ${value === NO_DATA ? 'text-slate-600' : tone}`}>
      {value}
    </div>
    <span className="text-[11px] text-slate-500 block">{hint}</span>
  </div>
);

const Bar: React.FC<{ label: string; count: number; total: number; color: string }> = ({
  label,
  count,
  total,
  color,
}) => (
  <div className="space-y-1">
    <div className="flex justify-between text-xs font-semibold">
      <span className="text-slate-300">{label}</span>
      <span className="text-slate-400">{count}</span>
    </div>
    <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
      <div
        className={`${color} h-full rounded-full transition-all duration-500`}
        // Guarded against total === 0, which previously produced NaN% and a
        // bar that silently failed to render.
        style={{ width: total > 0 ? `${(count / total) * 100}%` : '0%' }}
      />
    </div>
  </div>
);

const PerformanceTable: React.FC<{ title: string; rows: RatePerformance[]; nameFor?: (label: string) => string }> = ({
  title,
  rows,
  nameFor = (label: string) => label,
}) => (
  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
    <h3 className="text-sm font-bold text-slate-100">{title}</h3>

    {rows.length === 0 ? (
      <p className="text-xs text-slate-500">No applications tracked yet.</p>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-800">
              <th className="text-left font-semibold py-2">Name</th>
              <th className="text-right font-semibold py-2">Sent</th>
              <th className="text-right font-semibold py-2">Replies</th>
              <th className="text-right font-semibold py-2">Interviews</th>
              <th className="text-right font-semibold py-2">Reply rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.label} className="border-b border-slate-800/50 last:border-0">
                <td className="py-2 text-slate-200 font-medium truncate max-w-[180px]">
                  {nameFor(row.label)}
                </td>
                <td className="py-2 text-right text-slate-300">{row.applications}</td>
                <td className="py-2 text-right text-slate-300">{row.responses}</td>
                <td className="py-2 text-right text-slate-300">{row.interviews}</td>
                <td
                  className={`py-2 text-right font-semibold ${
                    row.responseRate === null ? 'text-slate-600' : 'text-cyan-400'
                  }`}
                >
                  {formatRate(row.responseRate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

export const AnalyticsOverview: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : 'Could not load analytics.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-12 text-center text-sm text-slate-500">Loading analytics…</div>;
  }

  if (error || !data) {
    return (
      <div className="flex items-start gap-2 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
        {error}
      </div>
    );
  }

  const funnelMax = Math.max(1, ...data.funnel.map(stage => stage.count));
  const sourceTotal = Object.values(data.jobsBySource).reduce((sum, n) => sum + n, 0);
  const freshnessTotal = Object.values(data.freshness).reduce((sum, n) => sum + n, 0);

  const sourceColors = ['bg-teal-500', 'bg-violet-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-amber-500'];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Applications tracked"
          value={String(data.totalApplications)}
          hint="Every job you have logged"
          icon={<Send className="w-4 h-4 text-indigo-400" />}
          tone="text-indigo-300"
        />
        <StatCard
          label="Reply rate"
          value={formatRate(data.responseRate)}
          hint={
            data.responseRate === null
              ? 'No applications sent yet'
              : 'Employers who came back, either way'
          }
          icon={<TrendingUp className="w-4 h-4 text-cyan-400" />}
          tone="text-cyan-300"
        />
        <StatCard
          label="Avg days to reply"
          value={data.avgDaysToResponse === null ? NO_DATA : String(data.avgDaysToResponse)}
          hint={
            data.avgDaysToResponse === null
              ? 'No replies recorded yet'
              : 'From applying to you logging a reply'
          }
          icon={<Clock className="w-4 h-4 text-amber-400" />}
          tone="text-amber-300"
        />
        <StatCard
          label="Avg match score"
          value={data.avgMatchScore === null ? NO_DATA : `${data.avgMatchScore}%`}
          hint={
            data.avgMatchScore === null
              ? 'No scored applications yet'
              : 'Across everything you applied to'
          }
          icon={<BarChart3 className="w-4 h-4 text-emerald-400" />}
          tone="text-emerald-300"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Application funnel
          </h3>
          {data.totalApplications === 0 ? (
            <p className="text-xs text-slate-500">
              Nothing tracked yet. Prepare an application from the Jobs tab and it appears here.
            </p>
          ) : (
            <div className="space-y-3">
              {data.funnel.map((stage, i) => (
                <Bar
                  key={stage.stage}
                  label={stage.stage}
                  count={stage.count}
                  total={funnelMax}
                  color={
                    ['bg-slate-500', 'bg-blue-500', 'bg-cyan-500', 'bg-teal-500', 'bg-emerald-500', 'bg-purple-500'][i] ||
                    'bg-slate-500'
                  }
                />
              ))}
            </div>
          )}
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-violet-400" />
            Jobs in the database by source
          </h3>
          {sourceTotal === 0 ? (
            <p className="text-xs text-slate-500">No jobs aggregated yet.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(data.jobsBySource)
                .sort((a, b) => b[1] - a[1])
                .map(([source, count], i) => (
                  <Bar
                    key={source}
                    label={sourceLabel(source)}
                    count={count}
                    total={sourceTotal}
                    color={sourceColors[i % sourceColors.length]}
                  />
                ))}
              <p className="text-[11px] text-slate-500 pt-1">
                {data.jobsInDatabase} distinct postings; the counts above total {sourceTotal}
                {sourceTotal > data.jobsInDatabase &&
                  ' because some were found on more than one board and merged'}
                .
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          Posting freshness across the database
        </h3>
        {freshnessTotal === 0 ? (
          <p className="text-xs text-slate-500">No jobs aggregated yet.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {Object.entries(data.freshness).map(([bucket, count]) => (
              <div
                key={bucket}
                className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 text-center"
              >
                <div className={`text-xl font-bold ${count > 0 ? 'text-slate-100' : 'text-slate-700'}`}>
                  {count}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">{bucket}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PerformanceTable title="Performance by resume" rows={data.byResume} />
        <PerformanceTable title="Performance by source" rows={data.bySource} nameFor={sourceLabel} />
      </div>
    </div>
  );
};
