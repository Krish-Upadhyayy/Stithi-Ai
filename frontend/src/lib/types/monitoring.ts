export type SessionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface CentreSummary {
  id: number;
  centre_code: string;
  name: string;
  location?: string | null;
  status: string;
}

export interface CameraSummary {
  id: number;
  name: string;
  source_type: string;
  source_url: string;
  is_active: boolean;
}

export interface CreatorSummary {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface MonitoringSession {
  id: number;
  centre_id: number;
  camera_id?: number | null;
  session_date: string;
  // Strictly an anonymous aggregate count per SRS §FR-03 & PRD §9
  physical_attendance: number;
  started_at?: string | null;
  ended_at?: string | null;
  status: SessionStatus;
  created_by?: number | null;
  created_at: string;
  updated_at: string;
  // Video & Snapshot Engine attributes
  video_file_path?: string | null;
  video_filename?: string | null;
  video_file_size?: number | null;
  video_duration_seconds?: number | null;
  video_fps?: number | null;
  video_width?: number | null;
  video_height?: number | null;
  video_total_frames?: number | null;
  video_processing_status?: 'NOT_STARTED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  video_error_message?: string | null;
  centre?: CentreSummary;
  camera?: CameraSummary;
  creator?: CreatorSummary;
  snapshots?: Snapshot[];
}

export interface CreateMonitoringSessionRequest {
  centre_id: number;
  camera_id: number;
  physical_attendance: number;
  session_date?: string;
}

export interface Snapshot {
  id: number;
  monitoring_session_id: number;
  file_path: string;
  captured_at: string;
  sequence_number: number;
  frame_time_seconds: number;
  width?: number | null;
  height?: number | null;
  processing_status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
}

export interface VideoUploadResponse {
  session_id: number;
  video_filename: string;
  file_size: number;
  duration_seconds?: number | null;
  fps?: number | null;
  width?: number | null;
  height?: number | null;
  total_frames?: number | null;
  status: string;
  message: string;
}

export interface VideoProcessResponse {
  session_id: number;
  snapshots_created: number;
  duration_seconds: number;
  interval_seconds: number;
  status: string;
  message: string;
}

export interface AttendanceObservation {
  id: number;
  snapshot_id: number;
  monitoring_session_id?: number | null;
  observed_count: number;
  detected_count: number;
  confidence_score?: number | null;
  min_confidence?: number | null;
  max_confidence?: number | null;
  confidence_threshold?: number | null;
  model_name: string;
  model_version: string;
  inference_time_ms?: number | null;
  inference_device?: string | null;
  processing_status: string;
  has_annotated_image: boolean;
  created_at: string;
}

export interface ProcessSessionAttendanceResponse {
  session_id: number;
  snapshots_processed: number;
  observations_created: number;
  model_name: string;
  model_version: string;
  status: string;
  message: string;
}

export interface InfrastructureObservation {
  id: number;
  snapshot_id: number;
  monitoring_session_id?: number | null;
  inventory_item_id?: number | null;
  asset_type: string;
  detected_quantity: number;
  detected_class?: string;
  detected_count?: number;
  confidence?: number | null;
  min_confidence?: number | null;
  max_confidence?: number | null;
  confidence_threshold?: number | null;
  model_name?: string;
  model_version: string;
  inference_time_ms?: number | null;
  inference_device?: string | null;
  processing_status?: string;
  has_annotated_image?: boolean;
  apparent_condition?: string;
  created_at: string;
}

export interface DetectedAssetSummary {
  asset_type: string;
  detected_class: string;
  count: number;
  detected_count: number;
  confidence?: number | null;
  min_confidence?: number | null;
  max_confidence?: number | null;
  status: string;
  mapped_inventory_item?: string | null;
}

export interface SnapshotInfrastructureResponse {
  snapshot_id: number;
  monitoring_session_id: number;
  detections: DetectedAssetSummary[];
  observations: InfrastructureObservation[];
  total_detected_assets: number;
  model_name: string;
  model_version: string;
  inference_time_ms?: number | null;
  status: string;
  message?: string | null;
  has_annotated_image: boolean;
}

export interface ProcessSessionInfrastructureResponse {
  session_id: number;
  snapshots_processed: number;
  observations_created: number;
  detected_summary: Record<string, number>;
  model_name: string;
  model_version: string;
  status: string;
  message: string;
}

export interface InfrastructureModelInfoResponse {
  model_name: string;
  model_version: string;
  is_available: boolean;
  weights_path?: string | null;
  device: string;
  confidence_threshold: number;
  target_classes: string[];
}

export interface AttendanceEvaluationMetrics {
  detection_metrics?: {
    precision: number;
    recall: number;
    f1_score: number;
    map50: number;
    true_positives: number;
    false_positives: number;
    false_negatives: number;
  };
  speed_metrics?: {
    avg_inference_time_ms: number;
    fps: number;
  };
  count_metrics?: {
    total_images: number;
    mae: number;
    rmse: number;
    mape?: number | null;
    exact_match_pct: number;
    within_1_pct: number;
    within_2_pct: number;
  };
}

export interface AttendanceEvaluationResponse {
  status: 'EVALUATED' | 'NOT_EVALUATED';
  model_name?: string;
  model_version?: string;
  dataset_version?: string;
  evaluation_date?: string;
  registered_at?: string;
  selection_rationale?: string;
  metrics?: AttendanceEvaluationMetrics;
  message?: string;
}

export interface AttendanceModelInfoResponse {
  model_name: string;
  model_version: string;
  is_available: boolean;
  weights_path?: string | null;
  is_production_registered: boolean;
  device: string;
  confidence_threshold: number;
  production_metadata?: Record<string, unknown> | null;
}

export interface AttendanceComplianceResult {
  id?: number;
  monitoring_session_id: number;
  physical_attendance: number;
  ai_estimated_attendance?: number | null;
  difference?: number | null;
  tolerance: number;
  aggregation_method: string;
  valid_observation_count: number;
  total_snapshots_considered: number;
  status: 'MATCH' | 'DISCREPANCY' | 'INSUFFICIENT_DATA';
  calculated_at: string;
}

export interface InfrastructureComplianceItem {
  id?: number;
  monitoring_session_id: number;
  inventory_item_id?: number | null;
  item_name: string;
  ai_class?: string | null;
  expected_quantity: number;
  observed_quantity?: number | null;
  difference?: number | null;
  aggregation_method: string;
  valid_observation_count: number;
  total_snapshots_considered: number;
  status: 'COMPLIANT' | 'DISCREPANCY' | 'NOT_MONITORED' | 'INSUFFICIENT_DATA';
  calculated_at: string;
}

export interface SessionComplianceResponse {
  session_id: number;
  calculated_at?: string | null;
  attendance?: AttendanceComplianceResult | null;
  infrastructure: InfrastructureComplianceItem[];
}

export interface ComplianceDashboardSummary {
  total_sessions_evaluated: number;
  attendance_matches: number;
  attendance_discrepancies: number;
  infrastructure_discrepancies: number;
  insufficient_data_sessions: number;
  last_calculated_at?: string | null;
}
