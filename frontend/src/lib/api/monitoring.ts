import { fetchApi } from './client';
import { MonitoringSession, CreateMonitoringSessionRequest } from '../types/monitoring';

export const monitoringApi = {
  /**
   * Retrieves all monitoring sessions with optional filtering by centre, status, or date.
   */
  async listSessions(params?: { centre_id?: number; status?: string; date?: string }): Promise<MonitoringSession[]> {
    const query = new URLSearchParams();
    if (params?.centre_id) query.append('centre_id', params.centre_id.toString());
    if (params?.status) query.append('status', params.status);
    if (params?.date) query.append('session_date', params.date);

    const queryString = query.toString();
    const endpoint = queryString ? `monitoring/sessions?${queryString}` : 'monitoring/sessions';
    return fetchApi<MonitoringSession[]>(endpoint, { cache: 'no-store' });
  },

  /**
   * Retrieves full details of a specific monitoring session.
   */
  async getSession(id: number): Promise<MonitoringSession> {
    return fetchApi<MonitoringSession>(`monitoring/sessions/${id}`, { cache: 'no-store' });
  },

  /**
   * Creates a new monitoring session with anonymous physical attendance headcount.
   * Session starts in PENDING status.
   */
  async createSession(data: CreateMonitoringSessionRequest): Promise<MonitoringSession> {
    return fetchApi<MonitoringSession>('monitoring/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Transitions a PENDING session to RUNNING and records the start timestamp.
   */
  async startSession(id: number): Promise<MonitoringSession> {
    return fetchApi<MonitoringSession>(`monitoring/sessions/${id}/start`, {
      method: 'POST',
    });
  },

  /**
   * Transitions a RUNNING session to COMPLETED and records the end timestamp.
   */
  async completeSession(id: number): Promise<MonitoringSession> {
    return fetchApi<MonitoringSession>(`monitoring/sessions/${id}/complete`, {
      method: 'POST',
    });
  },

  /**
   * Upload an MP4 video file to be associated with a monitoring session.
   */
  async uploadVideo(sessionId: number, file: File): Promise<import('../types/monitoring').VideoUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('video_file', file);
    return fetchApi<import('../types/monitoring').VideoUploadResponse>(`monitoring/sessions/${sessionId}/video`, {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Triggers periodic frame snapshot extraction from an uploaded video.
   */
  async processVideo(
    sessionId: number,
    intervalSeconds?: number
  ): Promise<import('../types/monitoring').VideoProcessResponse> {
    return fetchApi<import('../types/monitoring').VideoProcessResponse>(
      `monitoring/sessions/${sessionId}/process-video`,
      {
        method: 'POST',
        body: JSON.stringify(intervalSeconds ? { interval_seconds: intervalSeconds } : {}),
      }
    );
  },

  /**
   * Retrieves all periodic snapshots extracted for a monitoring session.
   */
  async listSnapshots(sessionId: number): Promise<import('../types/monitoring').Snapshot[]> {
    return fetchApi<import('../types/monitoring').Snapshot[]>(
      `monitoring/sessions/${sessionId}/snapshots`,
      { cache: 'no-store' }
    );
  },

  /**
   * Securely fetches snapshot JPEG blob using Bearer token authentication.
   */
  async fetchSnapshotImageBlob(snapshotId: number): Promise<Blob> {
    const { BASE_URL, getAuthToken } = await import('./client');
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${BASE_URL}/monitoring/snapshots/${snapshotId}/image`, {
      headers,
    });
    if (!res.ok) {
      throw new Error(`Failed to load snapshot: ${res.statusText}`);
    }
    return res.blob();
  },

  /**
   * Processes all snapshots of a monitoring session through Stithi AI presence detector.
   */
  async processSessionAttendance(
    sessionId: number,
    confidenceThreshold?: number
  ): Promise<import('../types/monitoring').ProcessSessionAttendanceResponse> {
    return fetchApi<import('../types/monitoring').ProcessSessionAttendanceResponse>(
      `monitoring/sessions/${sessionId}/attendance/process`,
      {
        method: 'POST',
        body: JSON.stringify(confidenceThreshold ? { confidence_threshold: confidenceThreshold } : {}),
      }
    );
  },

  /**
   * Retrieves all attendance observations recorded for a session.
   */
  async getSessionAttendanceObservations(
    sessionId: number
  ): Promise<import('../types/monitoring').AttendanceObservation[]> {
    return fetchApi<import('../types/monitoring').AttendanceObservation[]>(
      `monitoring/sessions/${sessionId}/attendance/observations`,
      { cache: 'no-store' }
    );
  },

  /**
   * Securely fetches annotated evidence snapshot image with bounding boxes.
   */
  async fetchAnnotatedObservationImageBlob(observationId: number): Promise<Blob> {
    const { BASE_URL, getAuthToken } = await import('./client');
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${BASE_URL}/monitoring/attendance/observations/${observationId}/annotated`, {
      headers,
    });
    if (!res.ok) {
      throw new Error(`Failed to load annotated evidence: ${res.statusText}`);
    }
    return res.blob();
  },

  /**
   * Retrieves verified evaluation metrics for the active attendance model.
   * Returns 'NOT_EVALUATED' if benchmarks have not yet been executed.
   */
  async getAttendanceEvaluation(): Promise<import('../types/monitoring').AttendanceEvaluationResponse> {
    return fetchApi<import('../types/monitoring').AttendanceEvaluationResponse>(
      'ai/attendance/evaluation',
      { cache: 'no-store' }
    );
  },

  /**
   * Retrieves active attendance model information and deployment state.
   */
  async getAttendanceModelInfo(): Promise<import('../types/monitoring').AttendanceModelInfoResponse> {
    return fetchApi<import('../types/monitoring').AttendanceModelInfoResponse>(
      'ai/attendance/model-info',
      { cache: 'no-store' }
    );
  },

  /**
   * Runs Stithi AI infrastructure asset detection on a single snapshot.
   */
  async detectSnapshotInfrastructure(
    snapshotId: number,
    options?: { confidence_threshold?: number; render_annotated?: boolean }
  ): Promise<import('../types/monitoring').SnapshotInfrastructureResponse> {
    return fetchApi<import('../types/monitoring').SnapshotInfrastructureResponse>(
      `monitoring/snapshots/${snapshotId}/infrastructure`,
      {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }
    );
  },

  /**
   * Batch processes all snapshots in a monitoring session through Stithi AI Infrastructure detector.
   */
  async processSessionInfrastructure(
    sessionId: number,
    options?: { confidence_threshold?: number }
  ): Promise<import('../types/monitoring').ProcessSessionInfrastructureResponse> {
    return fetchApi<import('../types/monitoring').ProcessSessionInfrastructureResponse>(
      `monitoring/sessions/${sessionId}/infrastructure/process`,
      {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }
    );
  },

  /**
   * Retrieves all infrastructure observations recorded for a session.
   */
  async getSessionInfrastructureObservations(
    sessionId: number
  ): Promise<import('../types/monitoring').InfrastructureObservation[]> {
    return fetchApi<import('../types/monitoring').InfrastructureObservation[]>(
      `monitoring/sessions/${sessionId}/infrastructure/observations`,
      { cache: 'no-store' }
    );
  },

  /**
   * Securely streams annotated infrastructure snapshot image blob.
   */
  async fetchAnnotatedInfrastructureImageBlob(observationId: number): Promise<Blob> {
    const { BASE_URL, getAuthToken } = await import('./client');
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${BASE_URL}/monitoring/infrastructure/observations/${observationId}/annotated`, {
      headers,
    });
    if (!res.ok) {
      throw new Error(`Failed to load annotated infrastructure evidence: ${res.statusText}`);
    }
    return res.blob();
  },

  /**
   * Retrieves active infrastructure model information and availability state.
   */
  async getInfrastructureModelInfo(): Promise<import('../types/monitoring').InfrastructureModelInfoResponse> {
    return fetchApi<import('../types/monitoring').InfrastructureModelInfoResponse>(
      'ai/infrastructure/model-info',
      { cache: 'no-store' }
    );
  },

  /**
   * Triggers deterministic compliance evaluation for attendance and infrastructure.
   */
  async calculateSessionCompliance(
    sessionId: number,
    params?: { tolerance?: number; aggregation_method?: string }
  ): Promise<import('../types/monitoring').SessionComplianceResponse> {
    return fetchApi<import('../types/monitoring').SessionComplianceResponse>(
      `monitoring/sessions/${sessionId}/compliance/calculate`,
      {
        method: 'POST',
        body: JSON.stringify(params || {}),
      }
    );
  },

  /**
   * Retrieves existing compliance records for a monitoring session.
   */
  async getSessionCompliance(
    sessionId: number
  ): Promise<import('../types/monitoring').SessionComplianceResponse> {
    return fetchApi<import('../types/monitoring').SessionComplianceResponse>(
      `monitoring/sessions/${sessionId}/compliance`,
      { cache: 'no-store' }
    );
  },

  /**
   * Retrieves real database compliance metrics summary across all evaluated sessions.
   */
  async getComplianceDashboardSummary(): Promise<import('../types/monitoring').ComplianceDashboardSummary> {
    return fetchApi<import('../types/monitoring').ComplianceDashboardSummary>(
      'monitoring/compliance/summary',
      { cache: 'no-store' }
    );
  },
};
