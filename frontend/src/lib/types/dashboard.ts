/**
 * TypeScript interfaces for Dashboard summary, centre overviews, and live audit activity.
 */

export interface DashboardCentresSummary {
  total: number;
  active: number;
  inactive: number;
}

export interface DashboardSessionsSummary {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
}

export interface DashboardAlertsSummary {
  total: number;
  pending: number;
  verified: number;
  false_positive: number;
  attendance_discrepancies: number;
  infrastructure_discrepancies: number;
  high_severity: number;
}

export interface DashboardComplianceSummary {
  attendance_matches: number;
  attendance_discrepancies: number;
  attendance_insufficient_data: number;
  infrastructure_compliant: number;
  infrastructure_discrepancies: number;
  infrastructure_insufficient_data: number;
  infrastructure_not_monitored: number;
}

export interface DashboardSummary {
  centres: DashboardCentresSummary;
  monitoring_sessions: DashboardSessionsSummary;
  alerts: DashboardAlertsSummary;
  compliance: DashboardComplianceSummary;
}

export interface CentreOverviewItem {
  id: number;
  name: string;
  centre_code: string;
  location?: string | null;
  status: string;
  camera_count: number;
  latest_session_id?: number | null;
  latest_session_date?: string | null;
  latest_session_status?: string | null;
  latest_attendance_compliance?: string | null;
  latest_infrastructure_compliance?: string | null;
  pending_alerts_count: number;
}

export interface RecentActivityItem {
  id: string;
  activity_type: string;
  title: string;
  description: string;
  timestamp: string;
  centre_id: number;
  centre_name: string;
  centre_code: string;
  session_id?: number | null;
  alert_id?: number | null;
}
