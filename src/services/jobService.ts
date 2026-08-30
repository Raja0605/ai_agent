import type {
  ApplicationLog,
  ApplicationStatus,
  FilterState,
  FreshnessFilter,
  JobPost,
} from '../types/job';
import { API_BASE_URL, fetchWithRetry } from '../config/api';

/**
 * Hours between `postedAt` and now.
 *
 * Returns null when the source gave no date. The previous mappers hardcoded
 * this to 0, which meant every job claimed to be brand new: the freshness
 * filter matched everything and the "posted in the last hour" analytics tile
 * counted the entire result set.
 */
export function hoursSince(postedAt: string | null | undefined): number | null {
  if (!postedAt) return null;

  const posted = new Date(postedAt).getTime();
  if (Number.isNaN(posted)) return null;

  const hours = (Date.now() - posted) / 3_600_000;
  // Clock skew between the source and the browser can produce a small
  // negative age; treat anything in the future as "just posted".
  return hours < 0 ? 0 : hours;
}

/** "3 hours ago" / "2 days ago" / "Date unknown". */
export function relativeTime(hours: number | null): string {
  if (hours === null) return 'Date unknown';
  if (hours < 1) {
    const minutes = Math.max(1, Math.round(hours * 60));
    return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
  }
  if (hours < 24) {
    const whole = Math.round(hours);
    return `${whole} hour${whole === 1 ? '' : 's'} ago`;
  }
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`;
  const months = Math.round(days / 30);
  return `${months} month${months === 1 ? '' : 's'} ago`;
}

const LAKH = 100_000;
const CRORE = 10_000_000;

/**
 * Render an INR figure the way the Indian market reads it.
 *
 * "₹18L" and "₹1.2 Cr" are how salaries are quoted and understood here;
 * "1,800,000 INR" is technically correct and effectively unreadable to the
 * audience. Note also that Indian digit grouping is 2-2-3 (₹18,00,000), which
 * `toLocaleString('en-IN')` handles and the default locale does not.
 */
function formatInr(value: number): string {
  if (value >= CRORE) {
    return `₹${Number((value / CRORE).toFixed(2))} Cr`;
  }
  if (value >= LAKH) {
    return `₹${Number((value / LAKH).toFixed(1))}L`;
  }
  return `₹${value.toLocaleString('en-IN')}`;
}

function formatSalary(job: Record<string, any>): string {
  const { salary_min: min, salary_max: max, currency } = job;
  if (!min && !max) return 'Not disclosed';

  if (currency === 'INR') {
    if (min && max) return `${formatInr(min)} – ${formatInr(max)} PA`;
    return `${formatInr(min || max)} PA`;
  }

  const unit = currency || '';
  const format = (value: number) => value.toLocaleString();

  if (min && max) return `${format(min)} – ${format(max)} ${unit}`.trim();
  return `From ${format(min || max)} ${unit}`.trim();
}

function formatExperience(job: Record<string, any>): string {
  const min = job.experience_min;
  const max = job.experience_max;
  if (min == null && max == null) return 'Experience not specified';
  if (min != null && max != null) return `${min}–${max} years`;
  return `${min ?? max}+ years`;
}

/**
 * Map an API job onto the client model.
 *
 * There used to be two of these — `fetchJobs` and `searchJobs` each had their
 * own copy, which drifted (different fallbacks, different platform handling).
 * One mapper, used by everything that receives a job.
 */
export function mapJob(job: Record<string, any>): JobPost {
  const sourceRecords: Record<string, any>[] = job.source_records || [];
  const primary = sourceRecords[0] || {};
  const postedAt: string | null = job.posted_at || null;
  const postedHoursAgo = hoursSince(postedAt);

  return {
    id: job.id,
    title: job.title || 'Untitled role',
    company: job.company || 'Unknown company',
    companyLogo: `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(
      (job.company || 'Unknown').replace(/\s+/g, '')
    )}`,
    location: job.location || 'Remote',
    isRemote: Boolean(job.remote),
    platform: primary.source || 'unknown',
    sources: sourceRecords.map(record => record.source).filter(Boolean),
    postedAt,
    postedHoursAgo,
    postedTime: relativeTime(postedHoursAgo),
    salary: formatSalary(job),
    experienceRequired: formatExperience(job),
    employmentType: job.employment_type ?? null,
    experienceMin: job.experience_min ?? null,
    experienceMax: job.experience_max ?? null,
    skillsRequired: (job.skills || []).map((skill: any) =>
      typeof skill === 'string' ? skill : skill.name
    ),
    description: job.description || 'No description provided.',
    applyUrl: primary.apply_url || primary.job_url || '',
  };
}

export function isWithinFreshnessWindow(
  postedHoursAgo: number | null,
  freshness: FreshnessFilter
): boolean {
  if (freshness === 'all') return true;
  if (postedHoursAgo === null) return true;  // Include jobs without dates
  const windows: Record<Exclude<FreshnessFilter, 'all'>, number> = {
    just_now: 1,
    '1_day': 24,
    '2_days': 48,
    '3_days': 72,
    past_week: 168,
  };
  return postedHoursAgo <= windows[freshness];
}

/**
 * Client-side filtering, restricted to the dimensions the server does not
 * already apply.
 *
 * `searchJobs` sends the keyword, location and remote flag to the API, which
 * filters on them upstream. Re-applying them here was double filtering: a
 * job matched by the API on its description could be dropped locally for not
 * matching on title, so search results silently disappeared.
 */
export function filterJobs(jobs: JobPost[], filter: FilterState): JobPost[] {
  return jobs.filter(job => {
    if (filter.platform !== 'all' && !job.sources.includes(filter.platform)) {
      return false;
    }
    if (!isWithinFreshnessWindow(job.postedHoursAgo, filter.freshness)) {
      return false;
    }
    return true;
  });
}

/** Distinct sources present in a result set, for building filter controls. */
export function availableSources(jobs: JobPost[]): string[] {
  const seen = new Set<string>();
  jobs.forEach(job => job.sources.forEach(source => seen.add(source)));
  return Array.from(seen).sort();
}

export async function searchJobs(filter: FilterState, useResume = false): Promise<JobPost[]> {
  const params = new URLSearchParams({
    remote: String(filter.remoteOnly),
    use_resume: String(useResume),
  });

  const keyword = filter.searchQuery.trim();
  const location = filter.location.trim();
  if (keyword) params.set('keyword', keyword);
  if (location) params.set('location', location);
  if (filter.experienceYears !== '' && filter.experienceYears !== 0) {
    params.set('min_experience', String(filter.experienceYears));
  }
  if (filter.experienceMin != null) params.set('min_experience', String(filter.experienceMin));
  if (filter.experienceMax != null) params.set('max_experience', String(filter.experienceMax));

  const response = await fetch(`${API_BASE_URL}/jobs/search?${params}`);
  if (!response.ok) {
    throw new Error(`Job search failed (${response.status})`);
  }

  const data = await response.json();
  return Array.isArray(data) ? data.map(mapJob) : [];
}

export async function getApplicationLogs(): Promise<ApplicationLog[]> {
  const response = await fetchWithRetry(`${API_BASE_URL}/applications/`);
  if (!response.ok) {
    throw new Error(`Could not load applications (${response.status})`);
  }

  const apps = await response.json();
  return apps.map((app: Record<string, any>) => ({
    id: app.id,
    jobId: app.job_id,
    jobTitle: app.job_title || 'Tracked job',
    company: app.company || 'Unknown company',
    platform: app.platform || 'unknown',
    appliedAt: app.applied_at || app.created_at,
    status: app.status as ApplicationStatus,
    resumeUsed: app.resume_used || 'Not recorded',
    // Null rather than 0 — "no score recorded" and "scored zero" are
    // different facts and the tracker displays them differently.
    matchScore: app.ats_score ?? null,
    coverNote: app.cover_note || '',
  }));
}

export async function addApplicationLog(log: {
  jobId: string;
  status: ApplicationStatus;
  resumeUsed: string;
  matchScore: number | null;
  coverNote?: string;
}): Promise<ApplicationLog[]> {
  const response = await fetch(`${API_BASE_URL}/applications/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: log.jobId,
      status: log.status,
      resume_used: log.resumeUsed,
      ats_score: log.matchScore,
      cover_note: log.coverNote,
    }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Could not track this application (${response.status})`);
  }

  return getApplicationLogs();
}

export async function updateApplicationStatus(
  id: string,
  newStatus: ApplicationStatus
): Promise<ApplicationLog[]> {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus }),
  });

  if (!response.ok) {
    throw new Error(`Could not update status (${response.status})`);
  }

  return getApplicationLogs();
}
