/**
 * Unified Python FastAPI Backend API client for SIH Training Centre AI Monitoring System
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = {
  getBackendUrl: (endpoint: string) => `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`,

  async getHealth() {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      return await res.json();
    } catch {
      return { status: 'DOWN', error: 'FastAPI backend unreachable' };
    }
  }
};
