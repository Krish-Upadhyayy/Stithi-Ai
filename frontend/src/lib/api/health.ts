import { fetchApi } from './client';
import { HealthStatus } from '../types/health';

export const healthApi = {
  /**
   * Fetches the backend health status from /api/v1/health
   */
  async getHealth(): Promise<HealthStatus> {
    return fetchApi<HealthStatus>('health', { cache: 'no-store' });
  },
};
