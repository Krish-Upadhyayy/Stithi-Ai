/**
 * Dashboard API client calling backend /api/v1/dashboard routes.
 */

import { fetchApi } from './client';
import {
  DashboardSummary,
  CentreOverviewItem,
  RecentActivityItem,
} from '../types/dashboard';

export const dashboardApi = {
  /**
   * Retrieves unified system-wide or centre-scoped metrics summary.
   */
  async getSummary(): Promise<DashboardSummary> {
    return fetchApi<DashboardSummary>('/api/v1/dashboard/summary', {
      method: 'GET',
    });
  },

  /**
   * Retrieves per-centre operational overview with latest session and pending alert counts.
   */
  async getCentresOverview(limit?: number): Promise<CentreOverviewItem[]> {
    const query = limit ? `?limit=${limit}` : '';
    return fetchApi<CentreOverviewItem[]>(`/api/v1/dashboard/centres-overview${query}`, {
      method: 'GET',
    });
  },

  /**
   * Retrieves chronological audit activity feed.
   */
  async getRecentActivity(limit = 10): Promise<RecentActivityItem[]> {
    return fetchApi<RecentActivityItem[]>(`/api/v1/dashboard/recent-activity?limit=${limit}`, {
      method: 'GET',
    });
  },
};
