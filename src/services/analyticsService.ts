import type { AnalyticsData, RatePerformance } from '../types/job';
import { API_BASE_URL, fetchWithRetry } from '../config/api';

function mapPerformance(data: Record<string, any>): RatePerformance {
  return {
    label: data.label,
    applications: data.applications,
    responses: data.responses,
    interviews: data.interviews,
    offers: data.offers,
    // Preserved as null, not coerced to 0: "no applications yet" and "a 0%
    // response rate" are different claims and only one of them is earned.
    responseRate: data.response_rate ?? null,
    avgMatchScore: data.avg_match_score ?? null,
  };
}

export async function getAnalytics(): Promise<AnalyticsData> {
  const response = await fetchWithRetry(`${API_BASE_URL}/analytics/`);
  if (!response.ok) throw new Error(`Could not load analytics (${response.status})`);

  const data = await response.json();
  return {
    totalApplications: data.total_applications,
    byStatus: data.by_status || {},
    funnel: data.funnel || [],
    responseRate: data.response_rate ?? null,
    interviewRate: data.interview_rate ?? null,
    offerRate: data.offer_rate ?? null,
    avgDaysToResponse: data.avg_days_to_response ?? null,
    avgMatchScore: data.avg_match_score ?? null,
    byResume: (data.by_resume || []).map(mapPerformance),
    bySource: (data.by_source || []).map(mapPerformance),
    jobsInDatabase: data.jobs_in_database ?? 0,
    jobsBySource: data.jobs_by_source || {},
    freshness: data.freshness || {},
  };
}
