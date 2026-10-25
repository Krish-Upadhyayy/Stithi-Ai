'use client';

import React, { useState, useEffect, useCallback, use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Video,
  Layers,
  AlertCircle,
  Check,
  Maximize2,
  FileText,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { SecureSnapshotImage } from '@/components/ui/SecureSnapshotImage';
import { alertsApi } from '@/lib/api/alerts';
import { Alert, AlertEvidence } from '@/lib/types/alert';

export default function AlertDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const alertId = Number(resolvedParams.id);

  const [alert, setAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review form state
  const [reviewerComment, setReviewerComment] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSuccess, setReviewSuccess] = useState<string | null>(null);

  // Evidence view options
  const [showAnnotated, setShowAnnotated] = useState(true);
  const [enlargedEvidence, setEnlargedEvidence] = useState<AlertEvidence | null>(null);

  const loadAlert = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await alertsApi.getAlert(alertId);
      setAlert(data);
      if (data.reviewer_comment) {
        setReviewerComment(data.reviewer_comment);
      }
    } catch (err) {
      console.error('Failed to load alert:', err);
      setError(err instanceof Error ? err.message : 'Unable to load alert.');
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    loadAlert();
  }, [loadAlert]);

  const handleReview = async (targetStatus: 'VERIFIED' | 'FALSE_POSITIVE') => {
    if (!alert) return;
    setReviewError(null);
    setReviewSuccess(null);

    if (targetStatus === 'FALSE_POSITIVE' && !reviewerComment.trim()) {
      setReviewError('A reviewer comment is mandatory when classifying an alert as FALSE POSITIVE.');
      return;
    }

    try {
      setReviewing(true);
      const updated = await alertsApi.reviewAlert(alert.id, {
        status: targetStatus,
        reviewer_comment: reviewerComment.trim() || undefined,
      });
      setAlert(updated);
      setReviewSuccess(`Alert successfully reviewed and marked as ${targetStatus}.`);
    } catch (err) {
      console.error('Review submission failed:', err);
      setReviewError(err instanceof Error ? err.message : 'Review action failed.');
    } finally {
      setReviewing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-sm">Loading alert details and attached evidence...</span>
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="space-y-4">
        <Link href="/alerts" className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Alerts Registry
        </Link>
        <Card className="p-6 border-rose-500/30 bg-rose-500/10 text-rose-300">
          <h2 className="text-base font-semibold">Alert Not Found or Access Denied</h2>
          <p className="text-xs text-rose-400 mt-1">{error || `Alert #${alertId} does not exist.`}</p>
        </Card>
      </div>
    );
  }

  const isFinalized = alert.status === 'VERIFIED' || alert.status === 'FALSE_POSITIVE';

  return (
    <div className="space-y-6">
      {/* Back Link & Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/alerts"
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Alerts Registry
        </Link>
        <div className="flex items-center gap-2">
          <Badge
            variant={
              alert.status === 'VERIFIED'
                ? 'success'
                : alert.status === 'FALSE_POSITIVE'
                ? 'outline'
                : 'warning'
            }
          >
            {alert.status}
          </Badge>
          <Badge
            variant={
              alert.severity === 'HIGH'
                ? 'danger'
                : alert.severity === 'MEDIUM'
                ? 'warning'
                : 'outline'
            }
          >
            {alert.severity} SEVERITY
          </Badge>
        </div>
      </div>

      <PageHeader
        title={`Alert #ALT-${alert.id}: ${alert.title}`}
        description={alert.description || 'Discrepancy notice generated from empirical Compliance Engine results.'}
        badge={
          <span className="font-mono text-xs text-cyan-400">
            {alert.alert_type === 'ATTENDANCE_DISCREPANCY'
              ? 'Attendance Headcount Discrepancy'
              : 'Sanctioned Asset Discrepancy'}
          </span>
        }
      />

      {/* Main Grid: Details & Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Metadata & Quantitative Summary */}
        <div className="space-y-6 lg:col-span-1">
          {/* Metadata Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                Alert Metadata
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs divide-y divide-slate-800/80">
              <div className="pt-2 first:pt-0 flex justify-between items-center">
                <span className="text-slate-400">Training Centre</span>
                <span className="font-medium text-white text-right">
                  {alert.centre_name || `Centre #${alert.centre_id}`}
                </span>
              </div>
              <div className="pt-2 flex justify-between items-center">
                <span className="text-slate-400">Monitoring Session</span>
                <span className="font-mono text-cyan-400">
                  Session #{alert.monitoring_session_id || alert.session_id}
                </span>
              </div>
              <div className="pt-2 flex justify-between items-center">
                <span className="text-slate-400">Discrepancy Category</span>
                <span className="text-slate-200">{alert.alert_type}</span>
              </div>
              <div className="pt-2 flex justify-between items-center">
                <span className="text-slate-400">Creation Timestamp</span>
                <span className="font-mono text-slate-300">
                  {new Date(alert.created_at).toLocaleString()}
                </span>
              </div>
              {alert.reviewed_at && (
                <div className="pt-2 flex justify-between items-center">
                  <span className="text-slate-400">Reviewed At</span>
                  <span className="font-mono text-slate-300">
                    {new Date(alert.reviewed_at).toLocaleString()}
                  </span>
                </div>
              )}
              {alert.reviewer_name && (
                <div className="pt-2 flex justify-between items-center">
                  <span className="text-slate-400">Reviewer</span>
                  <span className="font-medium text-emerald-400">{alert.reviewer_name}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quantitative Discrepancy Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                Discrepancy Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Expected</span>
                  <span className="text-lg font-bold font-mono text-white">
                    {alert.expected_value}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Observed</span>
                  <span className="text-lg font-bold font-mono text-cyan-400">
                    {alert.observed_value}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block uppercase">Variance</span>
                  <span className="text-lg font-bold font-mono text-amber-300">
                    {alert.difference}
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 italic">
                {alert.alert_type === 'ATTENDANCE_DISCREPANCY'
                  ? 'Attendance is estimated from periodic visual snapshots using Stithi AI. The system does not identify individuals.'
                  : 'Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.'}
              </p>
            </CardContent>
          </Card>

          {/* Human Review Action Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Human Review Decision
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {reviewSuccess && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-2">
                  <Check className="w-4 h-4" />
                  <span>{reviewSuccess}</span>
                </div>
              )}

              {reviewError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>{reviewError}</span>
                </div>
              )}

              {isFinalized ? (
                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={alert.status === 'VERIFIED' ? 'success' : 'outline'}>
                      {alert.status}
                    </Badge>
                    <span className="text-[11px] text-slate-400">
                      Reviewed on {new Date(alert.reviewed_at || '').toLocaleDateString()}
                    </span>
                  </div>
                  {alert.reviewer_comment ? (
                    <div className="mt-2 text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 block uppercase">Reviewer Comment</span>
                      &quot;{alert.reviewer_comment}&quot;
                    </div>
                  ) : null}
                  <p className="text-[11px] text-slate-500 italic mt-2">
                    Review status is locked and cannot be modified.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">
                      Reviewer Assessment Comment{' '}
                      <span className="text-slate-500">(Required for False Positive)</span>
                    </label>
                    <textarea
                      value={reviewerComment}
                      onChange={(e) => setReviewerComment(e.target.value)}
                      placeholder="Enter justification (e.g. CCTV frame shows camera obscured or physical discrepancy confirmed)..."
                      className="w-full h-24 p-2.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <Button
                      size="sm"
                      variant="primary"
                      className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs flex items-center justify-center gap-1.5"
                      disabled={reviewing}
                      onClick={() => handleReview('VERIFIED')}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {reviewing ? 'Submitting...' : 'Verify Alert'}
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      className="border-slate-700 hover:bg-slate-800 text-slate-300 text-xs flex items-center justify-center gap-1.5"
                      disabled={reviewing || !reviewerComment.trim()}
                      onClick={() => handleReview('FALSE_POSITIVE')}
                    >
                      <XCircle className="w-3.5 h-3.5 text-slate-400" />
                      False Positive
                    </Button>
                  </div>

                  {!reviewerComment.trim() && (
                    <p className="text-[10px] text-amber-400/80 italic">
                      * Type a comment above to enable the &quot;False Positive&quot; option.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Evidence Gallery */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Video className="w-4 h-4 text-cyan-400" />
                Supporting Snapshot Evidence ({alert.evidence?.length || 0})
              </CardTitle>

              <div className="flex items-center gap-2 text-xs">
                <button
                  onClick={() => setShowAnnotated(!showAnnotated)}
                  className={`px-2.5 py-1 rounded text-[11px] font-medium border transition-colors ${
                    showAnnotated
                      ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white'
                  }`}
                >
                  {showAnnotated ? 'Showing Annotated AI' : 'Showing Raw Snapshots'}
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {!alert.evidence || alert.evidence.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs rounded-xl bg-slate-900/40 border border-dashed border-slate-800">
                  No snapshot evidence records attached to this alert.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {alert.evidence.map((ev, idx) => (
                    <div
                      key={ev.id || idx}
                      onClick={() => setEnlargedEvidence(ev)}
                      className="group rounded-xl overflow-hidden border border-slate-800 bg-slate-950 hover:border-cyan-500/50 transition-all cursor-pointer flex flex-col justify-between"
                    >
                      <div className="relative aspect-video bg-slate-900 overflow-hidden">
                        <SecureSnapshotImage
                          snapshotId={ev.snapshot_id}
                          alt={`Evidence Snapshot #${ev.sequence_number || ev.snapshot_id}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                          isAnnotated={showAnnotated && ev.has_annotated_image}
                          observationId={ev.observation_id}
                          evidenceType={ev.evidence_type}
                        />
                        <div className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-950/80 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                          <Maximize2 className="w-3.5 h-3.5" />
                        </div>
                      </div>

                      <div className="p-3 text-xs space-y-1 bg-slate-950 border-t border-slate-800">
                        <div className="flex items-center justify-between font-mono">
                          <span className="text-cyan-400 font-semibold">
                            Frame #{ev.sequence_number || ev.snapshot_id}
                          </span>
                          <span className="text-slate-500 text-[10px]">
                            {ev.frame_time_seconds !== null && ev.frame_time_seconds !== undefined
                              ? `${ev.frame_time_seconds}s`
                              : ''}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span>
                            {ev.evidence_type === 'ATTENDANCE_SNAPSHOT'
                              ? 'Headcount Observed'
                              : 'Detected Presence'}
                            :
                          </span>
                          <span className="font-semibold text-white">
                            {ev.detected_count !== null && ev.detected_count !== undefined
                              ? ev.detected_count
                              : 'N/A'}
                          </span>
                        </div>

                        {ev.has_annotated_image && (
                          <div className="pt-1">
                            <span className="text-[10px] text-cyan-400/90 font-mono">
                              ✓ AI Bounding Box Rendered
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Enlarged Evidence Modal */}
      {enlargedEvidence && (
        <Modal
          isOpen={true}
          onClose={() => setEnlargedEvidence(null)}
          title={`Evidence Preview: Frame #${enlargedEvidence.sequence_number || enlargedEvidence.snapshot_id}`}
        >
          <div className="space-y-4">
            <div className="relative aspect-video max-h-[70vh] bg-slate-950 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center">
              <SecureSnapshotImage
                snapshotId={enlargedEvidence.snapshot_id}
                alt="Enlarged Snapshot Evidence"
                className="w-full h-full object-contain"
                isAnnotated={showAnnotated && enlargedEvidence.has_annotated_image}
                observationId={enlargedEvidence.observation_id}
                evidenceType={enlargedEvidence.evidence_type}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>
                Evidence Type: <span className="text-white">{enlargedEvidence.evidence_type}</span>
              </span>
              <span>
                Detected Count: <span className="text-cyan-400 font-mono">{enlargedEvidence.detected_count ?? 'N/A'}</span>
              </span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
