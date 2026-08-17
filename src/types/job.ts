export type Platform = 'all' | 'naukri' | 'indeed' | 'linkedin' | 'foundit' | 'glassdoor' | 'shine';

export type FreshnessFilter = 'all' | 'just_now' | '1_day' | '2_days' | '3_days' | 'past_week';

export type ExperienceFilter =
  | 'all'
  | 'resume_match'
  | 'fresher'
  | 'entry'
  | 'mid'
  | 'senior'
  | 'lead';

export type ExperienceFit = 'eligible' | 'stretch' | 'overqualified' | 'under_qualified';

export interface ExperienceRange {
  min: number;
  max: number;
}

export interface JobPost {
  id: string;
  title: string;
  company: string;
  companyLogo?: string;
  location: string;
  isRemote: boolean;
  platform: Platform;
  postedTime: string; // e.g. "Just now", "25 mins ago", "1 day ago"
  postedHoursAgo: number; // e.g., 0.5, 4, 24, 48, 72, 120
  salary: string;
  experienceRequired: string;
  skillsRequired: string[];
  description: string;
  applyUrl: string;
  applicantCount: number;
  featured?: boolean;
  atsMatchScore?: number;
  matchedSkills?: string[];
  missingSkills?: string[];
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

export interface ApplicationLog {
  id: string;
  jobId: string;
  jobTitle: string;
  company: string;
  platform: Platform;
  appliedAt: string;
  status: 'Submitted' | 'Under Review' | 'Interviewing' | 'Accepted' | 'Rejected';
  resumeUsed: string;
  atsScore: number;
  coverNote?: string;
}

export interface AiConfigState {
  activeProvider: 'google' | 'openai';
  googleApiKey: string;
  openaiApiKey: string;
  googleModel: string;
  openaiModel: string;
  embeddingsModel: string;
  useAiForMatching: boolean;
  useAiForCoverLetter: boolean;
}

export interface FilterState {
  searchQuery: string;
  platform: Platform;
  freshness: FreshnessFilter;
  experienceLevel: ExperienceFilter;
  resumeExperienceYears: number;
  remoteOnly: boolean;
  minSalary: number;
}
