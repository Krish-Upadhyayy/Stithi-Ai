export type AlertStatus = 'PENDING' | 'VERIFIED' | 'FALSE_POSITIVE';
export type AlertType = 'ATTENDANCE_DISCREPANCY' | 'INFRASTRUCTURE_DISCREPANCY';
export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

export interface AlertEvidence {
  id: number;
  alert_id: number;
  snapshot_id: number;
  sequence_number?: number | null;
  frame_time_seconds?: number | null;
  evidence_type: string;
  observation_id?: number | null;
  annotated_image_path?: string | null;
  has_annotated_image: boolean;
  detected_count?: number | null;
  confidence?: number | null;
  created_at: string;
}

export interface Alert {
  id: number;
  centre_id: number;
  centre_name?: string | null;
  centre_code?: string | null;
  session_id?: number | null;
  monitoring_session_id?: number | null;
  snapshot_id?: number | null;
  compliance_result_id?: number | null;
  inventory_item_id?: number | null;
  inventory_item_name?: string | null;
  alert_type: AlertType;
  severity: AlertSeverity;
  title: string;
  description?: string | null;
  expected_value: number;
  observed_value: number;
  detected_value?: number | null;
  difference: number;
  status: AlertStatus;
  created_at: string;
  updated_at?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: number | null;
  reviewer_name?: string | null;
  reviewer_comment?: string | null;
  evidence?: AlertEvidence[];
}

export interface AlertSummary {
  total_alerts: number;
  pending_alerts: number;
  verified_alerts: number;
  false_positive_alerts: number;
  attendance_discrepancies: number;
  infrastructure_discrepancies: number;
  high_severity_alerts: number;
}

export interface AlertGenerationResponse {
  session_id: number;
  alerts_created: number;
  alerts_existing: number;
  alerts: Alert[];
}
