'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Film,
  Camera,
  Users,
  Boxes,
  Scale,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RotateCw,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Modal } from '@/components/ui/Modal';
import { monitoringApi } from '@/lib/api/monitoring';
import { alertsApi } from '@/lib/api/alerts';
import {
  MonitoringSession,
  Snapshot,
  AttendanceObservation,
  InfrastructureObservation,
  SessionComplianceResponse,
} from '@/lib/types/monitoring';
import { Alert } from '@/lib/types/alert';
import { AttendanceTimelineChart } from '@/components/dashboard/AttendanceTimelineChart';
import { InfrastructureComparisonChart } from '@/components/dashboard/InfrastructureComparisonChart';

export default function MonitoringSessionDetailPage() {
  const params = useParams();
  const rawId = params?.id;
  const sessionId = Number(Array.isArray(rawId) ? rawId[0] : rawId);

  const [session, setSession] = useState<MonitoringSession | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [attendanceObs, setAttendanceObs] = useState<AttendanceObservation[]>([]);
  const [infraObs, setInfraObs] = useState<InfrastructureObservation[]>([]);
  const [compliance, setCompliance] = useState<SessionComplianceResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Snapshot Inspection Modal
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  const loadSessionData = useCallback(async () => {
    if (isNaN(sessionId)) {
      setError('Invalid Session ID specified.');
      setIsLoading(false);
      return;
    }

    try {
      const [
        sessionData,
        snapsData,
        attData,
        infraData,
        compData,
        alertsData,
      ] = await Promise.all([
        monitoringApi.getSession(sessionId),
        monitoringApi.listSnapshots(sessionId).catch(() => [] as Snapshot[]),
        monitoringApi.getSessionAttendanceObservations(sessionId).catch(() => [] as AttendanceObservation[]),
        monitoringApi.getSessionInfrastructureObservations(sessionId).catch(() => [] as InfrastructureObservation[]),
        monitoringApi.getSessionCompliance(sessionId).catch(() => null),
        alertsApi.listAlerts({ session_id: sessionId }).catch(() => [] as Alert[]),
      ]);

      setSession(sessionData);
      setSnapshots(snapsData);
      setAttendanceObs(attData);
      setInfraObs(infraData);
      setCompliance(compData);
      setAlerts(alertsData || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve session details.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadSessionData();
  }, [loadSessionData]);

  // Open Snapshot Modal and fetch secure image blob
  const handleOpenSnapshotModal = async (snap: Snapshot) => {
    setSelectedSnapshot(snap);
    setLoadingPreview(true);
    setPreviewBlobUrl(null);
    try {
      const blob = await monitoringApi.fetchSnapshotImageBlob(snap.id);
      const url = URL.createObjectURL(blob);
      setPreviewBlobUrl(url);
    } catch {
      // preview error handled in modal
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleCloseSnapshotModal = () => {
    if (previewBlobUrl) {
      URL.revokeObjectURL(previewBlobUrl);
    }
    setPreviewBlobUrl(null);
    setSelectedSnapshot(null);
  };

  // Pipeline execution triggers
  const handleProcessVideo = async () => {
    if (!session) return;
    setIsProcessing(true);
    setActionMessage(null);
    try {
      await monitoringApi.processVideo(session.id);
      setActionMessage('Video processed into periodic snapshots successfully.');
      await loadSessionData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Snapshot extraction failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunAttendanceAI = async () => {
    if (!session) return;
    setIsProcessing(true);
    setActionMessage(null);
    try {
      await monitoringApi.processSessionAttendance(session.id);
      setActionMessage('Attendance AI evaluated across snapshots successfully.');
      await loadSessionData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Attendance AI execution failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunInfrastructureAI = async () => {
    if (!session) return;
    setIsProcessing(true);
    setActionMessage(null);
    try {
      await monitoringApi.processSessionInfrastructure(session.id);
      setActionMessage('Infrastructure AI visual detections completed.');
      await loadSessionData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Infrastructure AI execution failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCalculateCompliance = async () => {
    if (!session) return;
    setIsProcessing(true);
    setActionMessage(null);
    try {
      await monitoringApi.calculateSessionCompliance(session.id);
      setActionMessage('Compliance rules evaluated against baselines.');
      await loadSessionData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Compliance calculation failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGenerateAlerts = async () => {
    if (!session) return;
    setIsProcessing(true);
    setActionMessage(null);
    try {
      const res = await alertsApi.generateAlertsForSession(session.id);
      setActionMessage(
        `Alerts generated: ${res.alerts_created} created, ${res.alerts_existing} existing verified.`
      );
      await loadSessionData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Alert generation failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading monitoring session pipeline..." />;
  }

  if (error || !session) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Monitoring Session"
          description="Detailed execution and AI observation record."
        />
        <ErrorState
          title="Session Not Found"
          message={error || 'Unable to locate monitoring session.'}
          onRetry={loadSessionData}
        />
      </div>
    );
  }

  // Progress Pipeline Stepper (Section 10)
  const steps = [
    { label: 'Session', done: session.id > 0, detail: `ID #${session.id}` },
    { label: 'Video', done: Boolean(session.video_file_path), detail: session.video_filename || 'Pending' },
    { label: 'Snapshots', done: snapshots.length > 0, detail: `${snapshots.length} frames` },
    { label: 'Attendance AI', done: attendanceObs.length > 0, detail: `${attendanceObs.length} runs` },
    { label: 'Infra AI', done: infraObs.length > 0, detail: `${infraObs.length} items` },
    { label: 'Compliance', done: Boolean(compliance?.calculated_at), detail: compliance?.attendance?.status || 'Pending' },
    { label: 'Alerts', done: alerts.length > 0 || (compliance?.attendance?.status === 'MATCH'), detail: `${alerts.length} flags` },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            href="/monitoring"
            className="text-xs text-slate-400 hover:text-white inline-flex items-center gap-1.5 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Monitoring Sessions</span>
          </Link>
          <PageHeader
            title={`Monitoring Session #${session.id}`}
            description={`Conducted at ${session.centre?.name || `Centre #${session.centre_id}`} on ${session.session_date}`}
            badge={
              <Badge
                variant={
                  session.status === 'COMPLETED'
                    ? 'success'
                    : session.status === 'RUNNING'
                    ? 'default'
                    : 'outline'
                }
              >
                {session.status}
              </Badge>
            }
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadSessionData}
            disabled={isProcessing}
            className="text-xs gap-1.5"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-emerald-400 hover:text-white">
            ×
          </button>
        </div>
      )}

      {/* Visual Pipeline Progress Stepper (Section 10) */}
      <Card className="p-4 bg-slate-900 border-slate-800">
        <p className="text-xs font-semibold text-slate-300 mb-3">Monitoring Pipeline Progress</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
          {steps.map((st, i) => (
            <div
              key={st.label}
              className={`p-2.5 rounded-lg border text-center transition-colors ${
                st.done
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-slate-800/40 border-slate-800 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <span className="text-[10px] font-mono opacity-70">0{i + 1}</span>
                {st.done ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                )}
              </div>
              <p className="text-xs font-semibold">{st.label}</p>
              <p className="text-[10px] opacity-75 truncate mt-0.5">{st.detail}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* AI Transparency & Privacy Assurance Banner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
        <div className="flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-emerald-400">
              Stithi AI Attendance • Privacy Assurance
            </p>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Attendance is estimated from periodic visual snapshots using Stithi AI. The system does not identify individuals. Monitoring uses aggregate visual counts and does not perform individual identity recognition.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-2.5 border-t md:border-t-0 md:border-l border-slate-800 pt-2 md:pt-0 md:pl-3">
          <Boxes className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-blue-400">
              Stithi AI Infrastructure • Visual Detection
            </p>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.
            </p>
          </div>
        </div>
      </div>

      {/* Action Trigger Toolbar (State Appropriate) */}
      <Card className="p-4 bg-slate-900/60 border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold text-slate-200">Pipeline Orchestration Actions</p>
            <p className="text-[11px] text-slate-400">
              Trigger AI inference, compliance calculations, and discrepancy alert generation
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {session.video_file_path && snapshots.length === 0 && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleProcessVideo}
                disabled={isProcessing}
                className="text-xs gap-1.5"
              >
                <Film className="w-3.5 h-3.5" />
                <span>Process Video Frames</span>
              </Button>
            )}

            {snapshots.length > 0 && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRunAttendanceAI}
                  disabled={isProcessing}
                  className="text-xs gap-1.5"
                >
                  <Users className="w-3.5 h-3.5 text-purple-400" />
                  <span>Run Attendance AI</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRunInfrastructureAI}
                  disabled={isProcessing}
                  className="text-xs gap-1.5"
                >
                  <Boxes className="w-3.5 h-3.5 text-blue-400" />
                  <span>Run Infrastructure AI</span>
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleCalculateCompliance}
                  disabled={isProcessing}
                  className="text-xs gap-1.5"
                >
                  <Scale className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Calculate Compliance</span>
                </Button>

                {compliance && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleGenerateAlerts}
                    disabled={isProcessing}
                    className="text-xs gap-1.5 bg-amber-600 hover:bg-amber-500"
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Generate Alerts</span>
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Two Column Grid: Session & Video Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Session Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Session Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Centre</span>
              <span className="font-semibold text-slate-200">
                {session.centre?.name || `ID #${session.centre_id}`} ({session.centre?.centre_code})
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Camera</span>
              <span className="text-slate-200">
                {session.camera?.name || (session.camera_id ? `Cam #${session.camera_id}` : 'None linked')}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Physical Attendance</span>
              <span className="font-mono text-emerald-400 font-bold">
                {session.physical_attendance} trainees
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Session Status</span>
              <Badge variant="outline">{session.status}</Badge>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Started / Completed</span>
              <span className="text-slate-400 font-mono">
                {session.started_at ? new Date(session.started_at).toLocaleTimeString() : '—'} /{' '}
                {session.ended_at ? new Date(session.ended_at).toLocaleTimeString() : '—'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Video & Snapshots Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Video & Snapshot Frame Stream</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Video Source File</span>
              <span className="font-mono text-slate-200 truncate max-w-[200px]">
                {session.video_filename || 'No video uploaded'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Duration & FPS</span>
              <span className="font-mono text-slate-200">
                {session.video_duration_seconds ? `${session.video_duration_seconds.toFixed(1)}s` : '—'} •{' '}
                {session.video_fps ? `${session.video_fps.toFixed(0)} FPS` : '—'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Resolution</span>
              <span className="font-mono text-slate-200">
                {session.video_width && session.video_height
                  ? `${session.video_width}x${session.video_height}`
                  : '—'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span className="text-slate-400">Extracted Snapshots</span>
              <span className="font-mono text-emerald-400 font-bold">
                {snapshots.length} snapshots
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Processing Status</span>
              <Badge variant="outline">{session.video_processing_status}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Attendance AI Section & Timeline Chart (Section 11) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Users className="w-4 h-4 text-purple-400" />
            <span>Attendance AI Analysis (Stithi AI Presence Detection)</span>
          </h3>
          {compliance?.attendance && (
            <Badge
              variant={
                compliance.attendance.status === 'MATCH'
                  ? 'success'
                  : compliance.attendance.status === 'DISCREPANCY'
                  ? 'danger'
                  : 'outline'
              }
            >
              Compliance: {compliance.attendance.status}
            </Badge>
          )}
        </div>
        <p className="text-[11px] text-slate-400">
          Attendance is estimated from periodic visual snapshots using Stithi AI. The system does not identify individuals.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1 p-4 space-y-3 text-xs">
            <p className="font-semibold text-slate-300">Attendance Breakdown</p>
            <div className="space-y-2 divide-y divide-slate-800">
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Physical Recorded</span>
                <span className="font-mono font-bold text-slate-200">
                  {session.physical_attendance}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">AI Estimated Headcount</span>
                <span className="font-mono font-bold text-emerald-400">
                  {compliance?.attendance?.ai_estimated_attendance != null
                    ? compliance.attendance.ai_estimated_attendance.toFixed(1)
                    : 'Not calculated'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Difference</span>
                <span className="font-mono text-slate-200">
                  {compliance?.attendance?.difference != null
                    ? compliance.attendance.difference.toFixed(1)
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Configured Tolerance</span>
                <span className="font-mono text-slate-200">
                  ±{compliance?.attendance?.tolerance ?? 2} trainees
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Aggregation Method</span>
                <span className="font-mono text-slate-200">
                  {compliance?.attendance?.aggregation_method ?? 'MEDIAN'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Valid Snapshot Frames</span>
                <span className="font-mono text-slate-200">
                  {compliance?.attendance?.valid_observation_count ?? 0}
                </span>
              </div>
            </div>
          </Card>

          <div className="lg:col-span-2">
            <AttendanceTimelineChart
              observations={attendanceObs}
              physicalAttendance={session.physical_attendance}
              aiEstimatedAttendance={compliance?.attendance?.ai_estimated_attendance}
              tolerance={compliance?.attendance?.tolerance ?? 2}
            />
          </div>
        </div>
      </div>

      {/* Infrastructure AI Section & Comparison Chart (Section 13) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Boxes className="w-4 h-4 text-blue-400" />
            <span>Infrastructure AI Analysis (Stithi AI Asset Detection)</span>
          </h3>
        </div>
        <p className="text-[11px] text-slate-400">
          Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-4 text-xs">
            <p className="font-semibold text-slate-300 mb-3">Sanctioned Items Comparison</p>
            {compliance?.infrastructure && compliance.infrastructure.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-950/40 border-b border-slate-800 text-slate-400 font-mono text-[10px] uppercase">
                    <tr>
                      <th className="py-2 px-3">Item</th>
                      <th className="py-2 px-3">Expected</th>
                      <th className="py-2 px-3">AI Observed</th>
                      <th className="py-2 px-3">Diff</th>
                      <th className="py-2 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-xs">
                    {compliance.infrastructure.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="py-2 px-3 font-medium text-slate-200">
                          {item.item_name}
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-300">
                          {item.expected_quantity}
                        </td>
                        <td className="py-2 px-3 font-mono text-emerald-400">
                          {item.observed_quantity != null ? item.observed_quantity.toFixed(0) : '—'}
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-300">
                          {item.difference != null ? item.difference.toFixed(0) : '—'}
                        </td>
                        <td className="py-2 px-3">
                          <Badge
                            variant={
                              item.status === 'COMPLIANT'
                                ? 'success'
                                : item.status === 'DISCREPANCY'
                                ? 'danger'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {item.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 text-center text-slate-500">
                No infrastructure compliance records calculated yet.
              </div>
            )}
          </Card>

          <InfrastructureComparisonChart items={compliance?.infrastructure || []} />
        </div>
      </div>

      {/* Discrepancy Alerts Generated for this Session */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Discrepancy Alerts for this Session</span>
            </CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Human review is required before treating any alert as verified
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            {alerts.length} Alerts
          </Badge>
        </CardHeader>
        <CardContent className="p-0">
          {alerts.length > 0 ? (
            <div className="divide-y divide-slate-800 text-xs">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="p-3.5 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          alert.severity === 'HIGH'
                            ? 'danger'
                            : alert.severity === 'MEDIUM'
                            ? 'warning'
                            : 'outline'
                        }
                      >
                        {alert.severity}
                      </Badge>
                      <span className="font-semibold text-slate-200">{alert.title}</span>
                    </div>
                    <p className="text-slate-400 text-[11px]">{alert.description}</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        alert.status === 'VERIFIED'
                          ? 'danger'
                          : alert.status === 'FALSE_POSITIVE'
                          ? 'success'
                          : 'warning'
                      }
                    >
                      {alert.status}
                    </Badge>
                    <Link href={`/alerts/${alert.id}`}>
                      <Button variant="outline" size="sm" className="text-xs h-7">
                        Review Evidence →
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500">
              No discrepancy alerts generated for this session.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Snapshots Frame Gallery */}
      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm">Periodic Snapshot Frames Gallery</CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              CCTV frames extracted periodically for AI evaluation and compliance audit
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {snapshots.length} Snapshots
          </span>
        </CardHeader>
        <CardContent className="p-4">
          {snapshots.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
              {snapshots.map((snap) => (
                <div
                  key={snap.id}
                  onClick={() => handleOpenSnapshotModal(snap)}
                  className="group relative cursor-pointer rounded-lg overflow-hidden border border-slate-800 hover:border-emerald-500/50 bg-slate-900 transition-all"
                >
                  <div className="aspect-video bg-slate-950 flex items-center justify-center text-slate-600 group-hover:text-emerald-400 transition-colors">
                    <Camera className="w-6 h-6" />
                  </div>
                  <div className="p-2 text-[10px]">
                    <p className="font-mono font-semibold text-slate-300">
                      Snap #{snap.id}
                    </p>
                    <p className="text-slate-500 truncate">
                      T: {snap.frame_time_seconds != null ? `${snap.frame_time_seconds.toFixed(0)}s` : '0s'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Film}
              title="No Snapshots Extracted"
              description="Upload an inspection video and click 'Process Video Frames' to extract periodic frames."
              className="py-10 border-0"
            />
          )}
        </CardContent>
      </Card>

      {/* Snapshot Preview Modal */}
      {selectedSnapshot && (
        <Modal
          isOpen={Boolean(selectedSnapshot)}
          onClose={handleCloseSnapshotModal}
          title={`Snapshot #${selectedSnapshot.id}`}
          description={`Captured at frame offset ${selectedSnapshot.frame_time_seconds?.toFixed(1) ?? 0}s`}
        >
          <div className="space-y-4 pt-2">
            <div className="rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center min-h-[250px]">
              {loadingPreview ? (
                <div className="p-8 text-xs text-slate-400 flex items-center gap-2">
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Loading secure snapshot frame...</span>
                </div>
              ) : previewBlobUrl ? (
                <img
                  src={previewBlobUrl}
                  alt={`Snapshot ${selectedSnapshot.id}`}
                  className="w-full h-auto object-contain max-h-[70vh]"
                />
              ) : (
                <p className="text-xs text-slate-500 p-8">Unable to load snapshot image.</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-slate-900 p-3 rounded-lg border border-slate-800">
              <div>
                <span className="text-slate-500">Processing: </span>
                <span className="text-slate-300">{selectedSnapshot.processing_status}</span>
              </div>
              <div>
                <span className="text-slate-500">File: </span>
                <span className="text-slate-300 truncate">{selectedSnapshot.file_path}</span>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
