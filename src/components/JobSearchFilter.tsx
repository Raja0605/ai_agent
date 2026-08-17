import React from 'react';
import { Building2, Calendar, Check, Clock, Filter, Globe, MapPin, Search, Sparkles, X, Zap } from 'lucide-react';
import type { FilterState, FreshnessFilter, Platform } from '../types/job';
import { sourceLabel } from './SourceBadge';

interface JobSearchFilterProps {
  filter: FilterState;
  setFilter: React.Dispatch<React.SetStateAction<FilterState>>;
  totalMatching: number;
  /** Sources present in the current results — the filter is built from these. */
  availableSources: string[];
  hasResume: boolean;
  onReset: () => void;
  onFetch: (useResume?: boolean) => void;
  isFetching?: boolean;
}

/**
 * Roles as they are actually advertised in the Indian market — the SDE ladder
 * rather than the US "Software Engineer II", and the stack acronyms local
 * postings are titled with.
 */
const POPULAR_ROLES = [
  'SDE',
  'Java Developer',
  'Full Stack Developer',
  'Data Engineer',
  'DevOps Engineer',
  'React Developer',
  'Python Developer',
  'QA Automation',
];

/** The cities carrying most of the country's tech hiring. */
const POPULAR_CITIES = [
  'Bengaluru',
  'Hyderabad',
  'Pune',
  'Chennai',
  'Gurugram',
  'Noida',
  'Mumbai',
];

const FRESHNESS_OPTIONS: { value: FreshnessFilter; label: string; icon?: React.ReactNode }[] = [
  { value: 'all', label: 'Any time' },
  { value: 'just_now', label: 'Last hour', icon: <Zap className="w-3 h-3" /> },
  { value: '1_day', label: 'Last 24 hours', icon: <Clock className="w-3 h-3" /> },
  { value: '3_days', label: 'Last 3 days', icon: <Calendar className="w-3 h-3" /> },
  { value: 'past_week', label: 'Last week', icon: <Calendar className="w-3 h-3" /> },
];

export const JobSearchFilter: React.FC<JobSearchFilterProps> = ({
  filter,
  setFilter,
  totalMatching,
  availableSources,
  hasResume,
  onReset,
  onFetch,
  isFetching = false,
}) => {
  const hasActiveFilters =
    filter.searchQuery !== '' ||
    filter.platform !== 'all' ||
    filter.freshness !== 'all' ||
    filter.remoteOnly ||
    filter.location !== '';

  const setPlatform = (platform: Platform) => setFilter(prev => ({ ...prev, platform }));
  const setFreshness = (freshness: FreshnessFilter) => setFilter(prev => ({ ...prev, freshness }));

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">

      {/* Search bar */}
      <div className="flex flex-col lg:flex-row items-center bg-slate-950/80 border border-slate-700 rounded-2xl lg:rounded-full p-2 gap-3 w-full shadow-inner">
        <div className="flex-1 flex items-center px-4 w-full lg:w-auto min-h-[48px]">
          <Search className="w-5 h-5 text-cyan-400 mr-3 shrink-0" />
          <input
            type="text"
            value={filter.searchQuery}
            onChange={e => setFilter(prev => ({ ...prev, searchQuery: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && onFetch(false)}
            placeholder="Role, skill or company"
            className="bg-transparent w-full focus:outline-none text-slate-100 placeholder-slate-500 font-medium text-[15px]"
          />
          {filter.searchQuery && (
            <button
              onClick={() => setFilter(prev => ({ ...prev, searchQuery: '' }))}
              className="p-1 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="hidden lg:block w-[1px] h-8 bg-slate-700" />

        <div className="w-full lg:w-56 flex items-center px-4 min-h-[48px]">
          <MapPin className="w-5 h-5 text-emerald-400 mr-3 shrink-0" />
          <input
            type="text"
            value={filter.location}
            onChange={e => setFilter(prev => ({ ...prev, location: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && onFetch(false)}
            placeholder="Location"
            className="bg-transparent w-full focus:outline-none text-slate-100 placeholder-slate-500 font-medium text-[15px]"
          />
        </div>

        <div className="flex gap-2 shrink-0 w-full lg:w-auto">
          <button
            onClick={() => onFetch(false)}
            disabled={isFetching}
            className="flex-1 lg:flex-none px-6 py-3.5 rounded-xl lg:rounded-full bg-slate-800 hover:bg-slate-700 text-white font-bold text-[15px] transition-all disabled:opacity-50"
          >
            {isFetching ? 'Searching…' : 'Search'}
          </button>
          <button
            onClick={() => onFetch(true)}
            disabled={isFetching || !hasResume}
            title={
              hasResume
                ? 'Search using the roles detected in your resume'
                : 'Upload a resume first — there is nothing to build a search from'
            }
            className="flex-1 lg:flex-none px-6 py-3.5 rounded-xl lg:rounded-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-[15px] shadow-lg shadow-blue-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Use my resume
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          Try:
        </span>
        {POPULAR_ROLES.map(role => (
          <button
            key={role}
            onClick={() => setFilter(prev => ({ ...prev, searchQuery: role }))}
            className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
              filter.searchQuery.toLowerCase() === role.toLowerCase()
                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-semibold'
                : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {role}
          </button>
        ))}
      </div>

      {/* City quick-picks. Typing either spelling works — the backend treats
          Bangalore and Bengaluru, Gurgaon and Gurugram as the same place —
          but these save the typing and show which markets are covered. */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <MapPin className="w-3 h-3 text-emerald-400" />
          Cities:
        </span>
        {POPULAR_CITIES.map(city => (
          <button
            key={city}
            onClick={() =>
              setFilter(prev => ({
                ...prev,
                location: prev.location.toLowerCase() === city.toLowerCase() ? '' : city,
              }))
            }
            className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
              filter.location.toLowerCase() === city.toLowerCase()
                ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 font-semibold'
                : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {city}
          </button>
        ))}
      </div>

      <div className="h-[1px] bg-slate-800/60" />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Source filter, built from the sources actually present in the
            results rather than a hardcoded list of portals we never query. */}
        <div className="lg:col-span-5 space-y-2">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-cyan-400" />
            Source
          </label>
          {availableSources.length === 0 ? (
            <p className="text-[11px] text-slate-500">Run a search to see which boards returned results.</p>
          ) : (
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => setPlatform('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  filter.platform === 'all'
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-bold'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                All sources
              </button>
              {availableSources.map(source => (
                <button
                  key={source}
                  onClick={() => setPlatform(source)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    filter.platform === source
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-bold'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sourceLabel(source)}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Freshness */}
        <div className="lg:col-span-7 space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              Posted within
            </label>
            <span className="text-[11px] text-slate-400">
              Showing <span className="font-semibold text-cyan-400">{totalMatching}</span> jobs
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {FRESHNESS_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => setFreshness(option.value)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                  filter.freshness === option.value
                    ? 'bg-amber-500/20 border-amber-400 text-amber-300'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
          {filter.freshness !== 'all' && (
            <p className="text-[11px] text-slate-500">
              Jobs whose source gave no posting date are excluded by this filter.
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => setFilter(prev => ({ ...prev, remoteOnly: !prev.remoteOnly }))}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-xs font-semibold transition-all ${
            filter.remoteOnly
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
              : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe className="w-4 h-4" />
          Remote only
          {filter.remoteOnly && <Check className="w-3.5 h-3.5 text-emerald-400" />}
        </button>

        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200 text-xs transition-all"
          >
            <Filter className="w-3.5 h-3.5" />
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
};
