/**
 * A job source is whatever the backend actually aggregates from. It is a
 * plain string rather than a union of hardcoded portal names: the UI used to
 * branch on 'naukri' | 'indeed' | 'linkedin' | 'foundit', none of which the
 * backend has ever fetched from, so those branches were permanently dead and
 * every real job fell through to a generic default.
 */
export type Platform = string;

export const ALL_PLATFORMS = 'all';

export type FreshnessFilter = 'all' | 'just_now' | '1_day' | '2_days' | '3_days' | 'past_week';

/** How a match number was produced. The UI must never present these alike. */
export type MatchMethod = 'ai' | 'heuristic';

/** How much evidence a score rests on — separate from how high it is. */
export type MatchConfidence = 'high' | 'medium' | 'low' | 'none';

export interface MatchResult {
  score: number;
  matchedSkills: string[];
  missingSkills: string[];
  summary: string;
  recommendations: string[];
  reason?: string;
  method: MatchMethod;
  confidence: MatchConfidence;
}

export interface JobPost {
  id: string;
  title: string;
  company: string;
  companyLogo?: string;
  location: string;
  isRemote: boolean;
  /** Primary source this listing came from. */
  platform: Platform;
  /** Every source this canonical job was seen on (cross-source dedup). */
  sources: Platform[];
  /** Absolute posted timestamp as returned by the API, if known. */
  postedAt: string | null;
  /** Human-readable relative age, e.g. "3 hours ago". */
  postedTime: string;
  /**
   * Age in hours, derived from postedAt. `null` when the source did not
   * provide a date — previously hardcoded to 0, which made every job look
   * brand new and rendered the freshness filter meaningless.
   */
  postedHoursAgo: number | null;
  salary: string;
  experienceRequired: string;
  skillsRequired: string[];
  description: string;
  applyUrl: string;
  /** Populated by batch scoring; undefined until a resume has been matched. */
  match?: MatchResult;
  sourceJobId?: string;
  featured?: boolean;
}

export interface ResumeProfile {
  id: string;
  fileName: string;
  uploadedAt: string;
  fileSize: string;
  fullName: string;
  email: string;
  phone: string;
  targetRole: string;
  summary: string;
  skills: string[];
  experienceYears: number;
  education: string;
  rawText?: string;
}

export type ApplicationStatus =
  | 'SAVED'
  | 'READY_TO_APPLY'
  | 'APPLYING'
  | 'APPLIED'
  | 'FAILED'
  | 'REJECTED'
  | 'INTERVIEW'
  | 'OFFER'
  | 'WITHDRAWN';

export interface ApplicationLog {
  id: string;
  jobId: string;
  jobTitle: string;
  company: string;
  platform: Platform;
  appliedAt: string;
  status: ApplicationStatus;
  resumeUsed: string;
  /** The match score recorded at the time of applying. */
  matchScore: number | null;
  coverNote?: string;
}

/**
 * The AI configuration actually in force, reported by the backend.
 *
 * This replaces a client-side config object whose model names were editable
 * in the UI but had no effect: credentials and model selection live in the
 * server environment, so the browser can only ever report what is set.
 */
export interface AiRuntimeConfig {
  provider: string;
  providerName: string;
  model: string;
  configured: boolean;
  activeMethod: MatchMethod;
}

export interface FilterState {
  searchQuery: string;
  platform: Platform;
  freshness: FreshnessFilter;
  experienceYears: number | '';
  location: string;
  remoteOnly: boolean;
  minSalary: number;
}

export interface JobLoop {
  id: string;
  name: string;
  keywords: string[];
  location: string | null;
  remoteOnly: boolean;
  resumeId: string | null;
  cadenceHours: number;
  minScore: number;
  active: boolean;
  lastRunAt: string | null;
  lastRunStatus: string | null;
  lastRunError: string | null;
  createdAt: string;
  totalMatches: number;
  newMatches: number;
}

export interface LoopMatch {
  id: string;
  loopId: string;
  score: number;
  scoreMethod: MatchMethod;
  matchedSkills: string[];
  missingSkills: string[];
  seen: boolean;
  createdAt: string;
  job: JobPost;
}

export interface LoopRunResult {
  loopId: string;
  status: string;
  jobsFetched: number;
  newMatches: number;
  belowThreshold: number;
  error?: string | null;
}

export interface AtsIssue {
  severity: 'critical' | 'warning' | 'info';
  message: string;
  fix: string;
}

export interface AtsCheckResult {
  score: number;
  issues: AtsIssue[];
  detectedSections: string[];
  wordCount: number;
}

export interface TailorResult {
  tailoredSummary: string;
  prioritizedSkills: string[];
  keywordsToAdd: string[];
  bulletSuggestions: string[];
  method: MatchMethod;
}

export interface RatePerformance {
  label: string;
  applications: number;
  responses: number;
  interviews: number;
  offers: number;
  /** null when there is no data to compute a rate from. */
  responseRate: number | null;
  avgMatchScore: number | null;
}

export interface AnalyticsData {
  totalApplications: number;
  byStatus: Record<string, number>;
  funnel: { stage: string; count: number }[];
  responseRate: number | null;
  interviewRate: number | null;
  offerRate: number | null;
  avgDaysToResponse: number | null;
  avgMatchScore: number | null;
  byResume: RatePerformance[];
  bySource: RatePerformance[];
  jobsInDatabase: number;
  jobsBySource: Record<string, number>;
  freshness: Record<string, number>;
}
