import React from 'react';
import { 
  Search, 
  Clock, 
  Zap, 
  Calendar, 
  Globe, 
  Check, 
  Filter, 
  X, 
  Sparkles,
  Building2
} from 'lucide-react';
import type { FilterState, FreshnessFilter, Platform } from '../types/job';

interface JobSearchFilterProps {
  filter: FilterState;
  setFilter: React.Dispatch<React.SetStateAction<FilterState>>;
  totalMatching: number;
  onReset: () => void;
}

const POPULAR_ROLES = [
  'DevOps Engineer',
  'Kubernetes Specialist',
  'Cloud Architect',
  'Site Reliability Engineer',
  'Frontend React',
  'Full Stack Node',
  'Data Engineer'
];

export const JobSearchFilter: React.FC<JobSearchFilterProps> = ({
  filter,
  setFilter,
  totalMatching,
  onReset
}) => {
  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter(prev => ({ ...prev, searchQuery: e.target.value }));
  };

  const handlePlatformChange = (platform: Platform) => {
    setFilter(prev => ({ ...prev, platform }));
  };

  const handleFreshnessChange = (freshness: FreshnessFilter) => {
    setFilter(prev => ({ ...prev, freshness }));
  };

  const selectRolePreset = (role: string) => {
    setFilter(prev => ({ ...prev, searchQuery: role }));
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      
      {/* 1. Job Title Search Input */}
      <div className="flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-cyan-400" />
          <input
            type="text"
            value={filter.searchQuery}
            onChange={handleQueryChange}
            placeholder="Search Job Title (e.g. DevOps, Kubernetes, Cloud, React, Data Engineer)..."
            className="w-full pl-12 pr-10 py-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 text-sm transition-all"
          />
          {filter.searchQuery && (
            <button
              onClick={() => setFilter(prev => ({ ...prev, searchQuery: '' }))}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Remote Only Toggle */}
        <button
          onClick={() => setFilter(prev => ({ ...prev, remoteOnly: !prev.remoteOnly }))}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-xs font-semibold whitespace-nowrap transition-all ${
            filter.remoteOnly
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-md shadow-emerald-500/10'
              : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe className="w-4 h-4" />
          Remote Jobs Only
          {filter.remoteOnly && <Check className="w-3.5 h-3.5 ml-1 text-emerald-400" />}
        </button>

        {/* Reset Filter Button */}
        {(filter.searchQuery || filter.platform !== 'all' || filter.freshness !== 'all' || filter.remoteOnly) && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-3 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200 text-xs transition-all"
          >
            <Filter className="w-3.5 h-3.5" />
            Clear Filters
          </button>
        )}
      </div>

      {/* Quick Role Suggestions */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          Suggested Roles:
        </span>
        {POPULAR_ROLES.map(role => (
          <button
            key={role}
            onClick={() => selectRolePreset(role)}
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

      <div className="h-[1px] bg-slate-800/60" />

      {/* 2. Platform Selector & Freshness Filter Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Platform Selector Tabs */}
        <div className="lg:col-span-6 space-y-2">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-cyan-400" />
            Job Platform Source
          </label>
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => handlePlatformChange('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                filter.platform === 'all'
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-bold shadow-sm'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              🌐 All Platforms
            </button>
            <button
              onClick={() => handlePlatformChange('naukri')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                filter.platform === 'naukri'
                  ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-bold shadow-md shadow-blue-600/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              Naukri.com
            </button>
            <button
              onClick={() => handlePlatformChange('indeed')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                filter.platform === 'indeed'
                  ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300 font-bold shadow-md shadow-indigo-600/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-indigo-400" />
              Indeed
            </button>
            <button
              onClick={() => handlePlatformChange('linkedin')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                filter.platform === 'linkedin'
                  ? 'bg-sky-600/30 border-sky-500 text-sky-300 font-bold shadow-md shadow-sky-600/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-sky-400" />
              LinkedIn
            </button>
            <button
              onClick={() => handlePlatformChange('foundit')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                filter.platform === 'foundit'
                  ? 'bg-amber-600/30 border-amber-500 text-amber-300 font-bold shadow-md shadow-amber-600/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Foundit (Monster)
            </button>
          </div>
        </div>

        {/* 3. Freshness Filter Chips */}
        <div className="lg:col-span-6 space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              Posting Freshness Filter
            </label>
            <span className="text-[11px] text-slate-400">
              Showing <span className="font-semibold text-cyan-400">{totalMatching}</span> jobs
            </span>
          </div>
          
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => handleFreshnessChange('all')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                filter.freshness === 'all'
                  ? 'bg-slate-800 border-slate-700 text-white font-bold'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              All Time
            </button>

            <button
              onClick={() => handleFreshnessChange('just_now')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                filter.freshness === 'just_now'
                  ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-md shadow-emerald-500/20 animate-pulse'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="w-3 h-3 text-emerald-400" />
              Just Now (&lt;1 hr)
            </button>

            <button
              onClick={() => handleFreshnessChange('1_day')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                filter.freshness === '1_day'
                  ? 'bg-amber-500/20 border-amber-400 text-amber-300 shadow-md shadow-amber-500/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              🔥 1 Day Ago
            </button>

            <button
              onClick={() => handleFreshnessChange('2_days')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                filter.freshness === '2_days'
                  ? 'bg-indigo-500/20 border-indigo-400 text-indigo-300 shadow-md shadow-indigo-500/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Calendar className="w-3 h-3 text-indigo-400" />
              2 Days Ago
            </button>

            <button
              onClick={() => handleFreshnessChange('3_days')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1 ${
                filter.freshness === '3_days'
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-md shadow-cyan-500/20'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              ⏳ 3 Days Ago
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
