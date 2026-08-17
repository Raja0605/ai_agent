import type {
  ApplicationLog,
  ExperienceFilter,
  ExperienceFit,
  ExperienceRange,
  FilterState,
  FreshnessFilter,
  JobPost,
  Platform
} from '../types/job';
import { INITIAL_JOBS } from '../data/mockJobs';

const APPLICATION_LOGS_KEY = 'job_pulse_application_logs';

// Years of experience covered by each named seniority band.
export const EXPERIENCE_BANDS: Record<Exclude<ExperienceFilter, 'all' | 'resume_match'>, ExperienceRange> = {
  fresher: { min: 0, max: 1 },
  entry: { min: 1, max: 3 },
  mid: { min: 3, max: 6 },
  senior: { min: 6, max: 10 },
  lead: { min: 10, max: 99 }
};

// A candidate may apply up to this many years below the advertised minimum.
const STRETCH_TOLERANCE_YEARS = 1;
// Above this many years past the advertised maximum the profile is over-qualified.
const OVERQUALIFIED_TOLERANCE_YEARS = 3;

// Parses free text such as "3 - 6 yrs", "5+ years" or "Fresher" into a year range.
export function parseExperienceRange(experienceRequired: string): ExperienceRange {
  const text = experienceRequired.toLowerCase();

  if (text.includes('fresher') || text.includes('intern')) {
    return { min: 0, max: 1 };
  }

  const numbers = text.match(/\d+(\.\d+)?/g)?.map(Number) ?? [];

  if (numbers.length === 0) {
    return { min: 0, max: 99 };
  }

  if (numbers.length === 1) {
    return { min: numbers[0], max: text.includes('+') ? 99 : numbers[0] };
  }

  return { min: Math.min(numbers[0], numbers[1]), max: Math.max(numbers[0], numbers[1]) };
}

export function rangesOverlap(a: ExperienceRange, b: ExperienceRange): boolean {
  return a.min <= b.max && b.min <= a.max;
}

// Classifies a candidate's total experience against what a job asks for.
export function getExperienceFit(job: JobPost, candidateYears: number): ExperienceFit {
  const { min, max } = parseExperienceRange(job.experienceRequired);

  if (candidateYears >= min && candidateYears <= max) return 'eligible';
  if (candidateYears >= min - STRETCH_TOLERANCE_YEARS && candidateYears < min) return 'stretch';
  if (candidateYears <= max + OVERQUALIFIED_TOLERANCE_YEARS && candidateYears > max) return 'overqualified';
  return candidateYears < min ? 'under_qualified' : 'overqualified';
}

// Jobs a candidate can realistically land: within range, or a one year stretch.
export function isExperienceMatch(job: JobPost, candidateYears: number): boolean {
  const fit = getExperienceFit(job, candidateYears);
  return fit === 'eligible' || fit === 'stretch';
}

export function matchesExperienceFilter(
  job: JobPost,
  experienceLevel: ExperienceFilter,
  candidateYears: number
): boolean {
  if (experienceLevel === 'all') return true;
  if (experienceLevel === 'resume_match') return isExperienceMatch(job, candidateYears);
  return rangesOverlap(parseExperienceRange(job.experienceRequired), EXPERIENCE_BANDS[experienceLevel]);
}

// Best matches first: eligible, then stretch, then closest to the candidate's profile.
export function sortByExperienceFit(jobs: JobPost[], candidateYears: number): JobPost[] {
  const rank: Record<ExperienceFit, number> = {
    eligible: 0,
    stretch: 1,
    overqualified: 2,
    under_qualified: 3
  };

  return [...jobs].sort((a, b) => {
    const diff = rank[getExperienceFit(a, candidateYears)] - rank[getExperienceFit(b, candidateYears)];
    if (diff !== 0) return diff;
    return a.postedHoursAgo - b.postedHoursAgo;
  });
}

export function filterJobs(jobs: JobPost[], filter: FilterState): JobPost[] {
  return jobs.filter(job => {
    // 1. Search Query Filter (Title, Company, Skills, Description)
    if (filter.searchQuery.trim()) {
      const q = filter.searchQuery.toLowerCase().trim();
      const matchTitle = job.title.toLowerCase().includes(q);
      const matchCompany = job.company.toLowerCase().includes(q);
      const matchSkill = job.skillsRequired.some(s => s.toLowerCase().includes(q));
      const matchDesc = job.description.toLowerCase().includes(q);
      if (!matchTitle && !matchCompany && !matchSkill && !matchDesc) {
        return false;
      }
    }

    // 2. Platform Filter
    if (filter.platform !== 'all' && job.platform !== filter.platform) {
      return false;
    }

    // 3. Freshness Filter
    if (filter.freshness !== 'all') {
      if (!isWithinFreshnessWindow(job.postedHoursAgo, filter.freshness)) {
        return false;
      }
    }

    // 4. Experience Filter (seniority band or resume based eligibility)
    if (!matchesExperienceFilter(job, filter.experienceLevel, filter.resumeExperienceYears)) {
      return false;
    }

    // 5. Remote Filter
    if (filter.remoteOnly && !job.isRemote) {
      return false;
    }

    return true;
  });
}

export function isWithinFreshnessWindow(postedHoursAgo: number, freshness: FreshnessFilter): boolean {
  switch (freshness) {
    case 'just_now':
      return postedHoursAgo <= 1.0;
    case '1_day':
      return postedHoursAgo <= 24.0;
    case '2_days':
      return postedHoursAgo <= 48.0;
    case '3_days':
      return postedHoursAgo <= 72.0;
    case 'past_week':
      return postedHoursAgo <= 168.0;
    default:
      return true;
  }
}

export function getApplicationLogs(): ApplicationLog[] {
  try {
    const saved = localStorage.getItem(APPLICATION_LOGS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (err) {
    console.error('Failed to load application logs:', err);
  }
  return [
    {
      id: 'app-sample-1',
      jobId: 'job-devops-naukri-2',
      jobTitle: 'DevOps Automation Lead (Kubernetes & Helm)',
      company: 'CloudMatrix Solutions',
      platform: 'naukri',
      appliedAt: 'Today at ' + new Date(Date.now() - 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'Submitted',
      resumeUsed: 'DevOps_Senior_Architect_Resume.pdf',
      atsScore: 94,
      coverNote: 'Auto-applied via JobPulse with attached DevOps Resume profile.'
    }
  ];
}

export function addApplicationLog(log: Omit<ApplicationLog, 'id'>): ApplicationLog[] {
  const logs = getApplicationLogs();
  const newLog: ApplicationLog = {
    ...log,
    id: 'app-' + Date.now()
  };
  const updated = [newLog, ...logs];
  localStorage.setItem(APPLICATION_LOGS_KEY, JSON.stringify(updated));
  return updated;
}
