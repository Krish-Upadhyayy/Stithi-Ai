import { fetchApi } from './client';
import { Alert, AlertSummary, AlertGenerationResponse } from '../types/alert';

export interface AlertFilterParams {
  status?: string;
  alert_type?: string;
  severity?: string;
  centre_id?: number;
  session_id?: number;
}

export const alertsApi = {
  /**
   * Retrieves compliance alerts with optional query filters.
   */
  async listAlerts(filters?: AlertFilterParams): Promise<Alert[]> {
    const query = new URLSearchParams();
    if (filters?.status && filters.status !== 'ALL') {
      query.append('status', filters.status);
    }
    if (filters?.alert_type && filters.alert_type !== 'ALL') {
      query.append('alert_type', filters.alert_type);
    }
    if (filters?.severity && filters.severity !== 'ALL') {
      query.append('severity', filters.severity);
    }
    if (filters?.centre_id) {
      query.append('centre_id', filters.centre_id.toString());
    }
    if (filters?.session_id) {
      query.append('session_id', filters.session_id.toString());
    }

    const qs = query.toString();
    const endpoint = qs ? `alerts?${qs}` : 'alerts';
    return fetchApi<Alert[]>(endpoint, { cache: 'no-store' });
  },

  /**
   * Retrieves single detailed alert record with attached evidence.
   */
  async getAlert(alertId: number): Promise<Alert> {
    return fetchApi<Alert>(`alerts/${alertId}`, { cache: 'no-store' });
  },

  /**
   * Submits human review decision (VERIFIED or FALSE_POSITIVE).
   */
  async reviewAlert(
    alertId: number,
    data: { status: 'VERIFIED' | 'FALSE_POSITIVE'; reviewer_comment?: string }
  ): Promise<Alert> {
    return fetchApi<Alert>(`alerts/${alertId}/review`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Legacy status update route.
   */
  async updateStatus(alertId: number, status: string): Promise<Alert> {
    return fetchApi<Alert>(`alerts/${alertId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  /**
   * Triggers idempotent alert generation for a monitoring session.
   */
  async generateAlertsForSession(sessionId: number): Promise<AlertGenerationResponse> {
    return fetchApi<AlertGenerationResponse>(`monitoring/sessions/${sessionId}/alerts/generate`, {
      method: 'POST',
    });
  },

  /**
   * Retrieves real database alert summary counts.
   */
  async getAlertSummary(): Promise<AlertSummary> {
    return fetchApi<AlertSummary>('alerts/summary', { cache: 'no-store' });
  },
};
