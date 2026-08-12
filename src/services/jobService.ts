import type { ApplicationLog, FilterState, FreshnessFilter, JobPost, Platform } from '../types/job';
import { INITIAL_JOBS } from '../data/mockJobs';

const APPLICATION_LOGS_KEY = 'job_pulse_application_logs';

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

    // 4. Remote Filter
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
