import React from 'react';

/**
 * Badge for whichever board a job came from.
 *
 * This replaces a switch over 'naukri' | 'indeed' | 'linkedin' | 'foundit'.
 * The backend has never fetched from any of those, so all four branches were
 * unreachable and every real job (Remotive, Adzuna) fell through to a generic
 * "Job Portal" label. Styling is derived from the source name instead, so a
 * new adapter gets a sensible badge without a UI change.
 */

type SourceStyle = {
  label: string;
  classes: string;
  /** Posted straight from the employer's own careers system. */
  direct?: boolean;
  /**
   * Reached through an aggregator that licenses the Google for Jobs index,
   * rather than fetched from the portal itself. Worth saying plainly: the
   * listing is real and the apply link goes to the portal, but it can lag the
   * portal by a few hours.
   */
  viaAggregator?: boolean;
};

const KNOWN_SOURCES: Record<string, SourceStyle> = {
  remotive: {
    label: 'Remotive',
    classes: 'bg-teal-500/15 border-teal-500/30 text-teal-300',
  },
  adzuna: {
    label: 'Adzuna',
    classes: 'bg-violet-500/15 border-violet-500/30 text-violet-300',
  },
  // The Indian portals. None of them can be queried directly — Naukri has no
  // public API, Indeed retired its Publisher API, LinkedIn gates job data
  // behind partnership — so these arrive through an aggregator, but each
  // keeps the identity of the portal it was published on.
  naukri: {
    label: 'Naukri',
    classes: 'bg-blue-500/15 border-blue-500/30 text-blue-300',
    viaAggregator: true,
  },
  linkedin: {
    label: 'LinkedIn',
    classes: 'bg-sky-500/15 border-sky-500/30 text-sky-300',
    viaAggregator: true,
  },
  indeed: {
    label: 'Indeed',
    classes: 'bg-indigo-500/15 border-indigo-500/30 text-indigo-300',
    viaAggregator: true,
  },
  foundit: {
    label: 'Foundit',
    classes: 'bg-purple-500/15 border-purple-500/30 text-purple-300',
    viaAggregator: true,
  },
  shine: {
    label: 'Shine',
    classes: 'bg-orange-500/15 border-orange-500/30 text-orange-300',
    viaAggregator: true,
  },
  timesjobs: {
    label: 'TimesJobs',
    classes: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
    viaAggregator: true,
  },
  instahyre: {
    label: 'Instahyre',
    classes: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300',
    viaAggregator: true,
  },
  hirist: {
    label: 'Hirist',
    classes: 'bg-fuchsia-500/15 border-fuchsia-500/30 text-fuchsia-300',
    viaAggregator: true,
  },
  internshala: {
    label: 'Internshala',
    classes: 'bg-lime-500/15 border-lime-500/30 text-lime-300',
    viaAggregator: true,
  },
  glassdoor: {
    label: 'Glassdoor',
    classes: 'bg-green-500/15 border-green-500/30 text-green-300',
  },
  google: {
    label: 'Google Jobs',
    classes: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
  },
  zip_recruiter: {
    label: 'ZipRecruiter',
    classes: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
  },
  bayt: {
    label: 'Bayt',
    classes: 'bg-orange-500/15 border-orange-500/30 text-orange-300',
  },
  bdjobs: {
    label: 'BDJobs',
    classes: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
  },
  wellfound: {
    label: 'Wellfound',
    classes: 'bg-slate-500/15 border-slate-500/30 text-slate-300',
    viaAggregator: true,
  },
  // The aggregators themselves, for listings whose original portal was not
  // reported.
  jsearch: {
    label: 'Google Jobs',
    classes: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    viaAggregator: true,
  },
  careerjet: {
    label: 'Careerjet',
    classes: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    viaAggregator: true,
  },
  jooble: {
    label: 'Jooble',
    classes: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    viaAggregator: true,
  },
  // Company career boards. These are first-party postings pulled from the
  // employer's own ATS, so they carry no aggregator lag and the apply link
  // goes straight to the real application — worth signalling to the user.
  greenhouse: {
    label: 'Company site',
    classes: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
    direct: true,
  },
  lever: {
    label: 'Company site',
    classes: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
    direct: true,
  },
  ashby: {
    label: 'Company site',
    classes: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
    direct: true,
  },
};

function boardKey(source: string): string {
  return source.startsWith('jobspy:') ? source.slice('jobspy:'.length) : source;
}

/** Whether a source posts straight from the employer's own careers system. */
export function isDirectSource(source: string): boolean {
  return Boolean(KNOWN_SOURCES[boardKey(source)]?.direct);
}

const FALLBACK_CLASSES = 'bg-slate-800 border-slate-700 text-slate-300';

export function sourceLabel(source: string): string {
  const key = boardKey(source);
  return KNOWN_SOURCES[key]?.label ?? key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
}

interface SourceBadgeProps {
  source: string;
  /** Every board this job was found on, when it was seen on more than one. */
  allSources?: string[];
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({ source, allSources }) => {
  const known = KNOWN_SOURCES[boardKey(source)];
  const extra = (allSources || []).filter(s => s !== source);

  return (
    <span className="flex items-center gap-1.5">
      <span
        className={`px-2.5 py-1 text-[11px] font-bold rounded-lg border flex items-center gap-1.5 ${
          known?.classes ?? FALLBACK_CLASSES
        }`}
        title={
          known?.direct
            ? `Posted directly by the employer (via ${source}) — you apply on their own site`
            : known?.viaAggregator
              ? `Published on ${sourceLabel(source)}, indexed through a jobs aggregator — the apply link goes to the original posting`
              : `Aggregated from ${sourceLabel(source)}`
        }
      >
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
        {sourceLabel(source)}
      </span>

      {/* Cross-source dedup made visible: the same posting on two boards is
          one card, and this says where else it was found. */}
      {extra.length > 0 && (
        <span
          className="px-2 py-1 text-[10px] font-semibold rounded-lg border border-slate-700 bg-slate-900 text-slate-400"
          title={`Also listed on ${extra.map(sourceLabel).join(', ')}`}
        >
          +{extra.length}
        </span>
      )}
    </span>
  );
};
