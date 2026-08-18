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

const EXPERIENCE_OPTIONS: { value: number | ''; label: string }[] = [
  { value: '', label: 'Any experience' },
  { value: 0, label: 'Fresher/Entry level' },
  { value: 1, label: '1+ years' },
  { value: 2, label: '2+ years' },
  { value: 3, label: '3+ years' },
  { value: 5, label: '5+ years' },
  { value: 8, label: '8+ years' },
  { value: 10, label: '10+ years' },
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
    filter.location !== '' ||
    filter.experienceYears !== '';

  const setPlatform = (platform: Platform) => setFilter(prev => ({ ...prev, platform }));
  const setFreshness = (freshness: FreshnessFilter) => setFilter(prev => ({ ...prev, freshness }));
  const setExperience = (years: number | '') => setFilter(prev => ({ ...prev, experienceYears: years }));

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-md space-y-6">

      {/* Search bar */}
      <div className="flex flex-col lg:flex-row items-center bg-gray-50 border border-gray-300 rounded-xl p-2 gap-3 w-full">
        <div className="flex-1 flex items-center px-4 w-full lg:w-auto min-h-[48px]">
          <Search className="w-5 h-5 text-blue-600 mr-3 shrink-0" />
          <input
            type="text"
            value={filter.searchQuery}
            onChange={e => setFilter(prev => ({ ...prev, searchQuery: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && onFetch(false)}
            placeholder="Role, skill or company"
            className="bg-transparent w-full focus:outline-none text-gray-900 placeholder-gray-500 font-medium text-[15px]"
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

        <div className="hidden lg:block w-[1px] h-8 bg-gray-300" />

        <div className="w-full lg:w-56 flex items-center px-4 min-h-[48px]">
          <MapPin className="w-5 h-5 text-green-600 mr-3 shrink-0" />
          <input
            type="text"
            value={filter.location}
            onChange={e => setFilter(prev => ({ ...prev, location: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && onFetch(false)}
            placeholder="Location"
            className="bg-transparent w-full focus:outline-none text-gray-900 placeholder-gray-500 font-medium text-[15px]"
          />
        </div>

        <div className="flex gap-2 shrink-0 w-full lg:w-auto">
          <button
            onClick={() => onFetch(false)}
            disabled={isFetching}
            className="flex-1 lg:flex-none px-6 py-3.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-white font-semibold text-[15px] transition-all disabled:opacity-50"
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
            className="flex-1 lg:flex-none px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-[15px] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Use my resume
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-blue-600" />
          Try:
        </span>
        {POPULAR_ROLES.map(role => (
          <button
            key={role}
            onClick={() => setFilter(prev => ({ ...prev, searchQuery: role }))}
            className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
              filter.searchQuery.toLowerCase() === role.toLowerCase()
                ? 'bg-blue-100 border-blue-300 text-blue-700 font-semibold'
                : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900 hover:border-gray-400'
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
        <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1">
          <MapPin className="w-3 h-3 text-green-600" />
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
                ? 'bg-green-100 border-green-300 text-green-700 font-semibold'
                : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900 hover:border-gray-400'
            }`}
          >
            {city}
          </button>
        ))}
      </div>

      <div className="h-[1px] bg-gray-200" />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Source filter, built from the sources actually present in the
            results rather than a hardcoded list of portals we never query. */}
        <div className="lg:col-span-5 space-y-2">
          <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-blue-600" />
            Source
          </label>
          {availableSources.length === 0 ? (
            <p className="text-[11px] text-gray-500">Run a search to see which boards returned results.</p>
          ) : (
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => setPlatform('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  filter.platform === 'all'
                    ? 'bg-blue-100 border-blue-300 text-blue-700 font-semibold'
                    : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900'
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
                      ? 'bg-blue-100 border-blue-300 text-blue-700 font-semibold'
                      : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900'
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
            <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-600" />
              Posted within
            </label>
            <span className="text-[11px] text-gray-600">
              Showing <span className="font-semibold text-blue-600">{totalMatching}</span> jobs
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {FRESHNESS_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => setFreshness(option.value)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                  filter.freshness === option.value
                    ? 'bg-amber-100 border-amber-300 text-amber-700'
                    : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900'
                }`}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
          {filter.freshness !== 'all' && (
            <p className="text-[11px] text-gray-500">
              Jobs whose source gave no posting date are excluded by this filter.
            </p>
          )}
        </div>

        {/* Experience filter */}
        <div className="lg:col-span-12 space-y-2">
          <label className="text-xs font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            Experience required
          </label>
          <div className="flex items-center gap-1.5 flex-wrap">
            {EXPERIENCE_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => setExperience(option.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  filter.experienceYears === option.value
                    ? 'bg-purple-100 border-purple-300 text-purple-700 font-semibold'
                    : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          {filter.experienceYears !== '' && (
            <p className="text-[11px] text-gray-500">
              Showing jobs requiring {filter.experienceYears === 0 ? 'entry-level' : `${filter.experienceYears}+ years`} experience.
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => setFilter(prev => ({ ...prev, remoteOnly: !prev.remoteOnly }))}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-semibold transition-all ${
            filter.remoteOnly
              ? 'bg-green-50 border-green-300 text-green-700'
              : 'bg-gray-50 border-gray-300 text-gray-600 hover:text-gray-900'
          }`}
        >
          <Globe className="w-4 h-4" />
          Remote only
          {filter.remoteOnly && <Check className="w-3.5 h-3.5 text-green-600" />}
        </button>

        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-600 hover:text-gray-900 text-xs transition-all"
          >
            <Filter className="w-3.5 h-3.5" />
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
};
