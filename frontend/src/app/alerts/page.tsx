'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  Filter,
  RefreshCw,
  Eye,
  Users,
  Box,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { alertsApi, AlertFilterParams } from '@/lib/api/alerts';
import { Alert, AlertSummary } from '@/lib/types/alert';

export default function AlertsListPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState(true);

  // Filter states
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  const fetchAlertsAndSummary = useCallback(async () => {
    try {
      setLoading(true);
      const filterParams: AlertFilterParams = {
        status: statusFilter,
        alert_type: typeFilter,
        severity: severityFilter,
      };

      const [alertsData, summaryData] = await Promise.all([
        alertsApi.listAlerts(filterParams),
        alertsApi.getAlertSummary().catch(() => null),
      ]);

      setAlerts(alertsData);
      if (summaryData) setSummary(summaryData);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter, severityFilter]);

  useEffect(() => {
    fetchAlertsAndSummary();
  }, [fetchAlertsAndSummary]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance Alerts & Human Review"
        description="Evidence-backed discrepancy notices generated from verified Compliance Engine calculations. All alerts require human reviewer confirmation before verification."
        badge={
          summary ? (
            <Badge variant="warning">{summary.pending_alerts} Pending Review</Badge>
          ) : (
            <Badge variant="outline">Review Workflow</Badge>
          )
        }
      />

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] text-slate-400 block">Total Alerts</span>
          <span className="text-xl font-bold font-mono text-white">
            {summary?.total_alerts ?? alerts.length}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-amber-500/20">
          <span className="text-[11px] text-amber-400 block flex items-center gap-1">
            <Clock className="w-3 h-3" /> Pending Review
          </span>
          <span className="text-xl font-bold font-mono text-amber-300">
            {summary?.pending_alerts ?? 0}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-emerald-500/20">
          <span className="text-[11px] text-emerald-400 block flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Verified
          </span>
          <span className="text-xl font-bold font-mono text-emerald-300">
            {summary?.verified_alerts ?? 0}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] text-slate-400 block flex items-center gap-1">
            <XCircle className="w-3 h-3" /> False Positives
          </span>
          <span className="text-xl font-bold font-mono text-slate-400">
            {summary?.false_positive_alerts ?? 0}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] text-cyan-400 block flex items-center gap-1">
            <Users className="w-3 h-3" /> Attendance
          </span>
          <span className="text-xl font-bold font-mono text-cyan-300">
            {summary?.attendance_discrepancies ?? 0}
          </span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] text-purple-400 block flex items-center gap-1">
            <Box className="w-3 h-3" /> Infrastructure
          </span>
          <span className="text-xl font-bold font-mono text-purple-300">
            {summary?.infrastructure_discrepancies ?? 0}
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800">
        <div className="flex items-center gap-3 flex-wrap text-xs">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending Review</option>
            <option value="VERIFIED">Verified Discrepancies</option>
            <option value="FALSE_POSITIVE">False Positives</option>
          </select>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Categories</option>
            <option value="ATTENDANCE_DISCREPANCY">Attendance Headcount</option>
            <option value="INFRASTRUCTURE_DISCREPANCY">Sanctioned Assets</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Severities</option>
            <option value="LOW">Low Severity</option>
            <option value="MEDIUM">Medium Severity</option>
            <option value="HIGH">High Severity</option>
          </select>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={fetchAlertsAndSummary}
          disabled={loading}
          className="text-xs flex items-center gap-1.5 text-slate-300"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Alerts Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
              <span className="text-xs">Loading alerts registry...</span>
            </div>
          ) : alerts.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title="No Alerts Found"
              description="No discrepancy alerts match your active filter criteria. Run compliance calculation on completed monitoring sessions to detect potential discrepancies."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Alert ID</th>
                    <th className="py-3 px-4">Centre & Session</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Discrepancy Details</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Evidence</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                  {(() => {
                    const sortedAlerts = [...alerts].sort((a, b) => {
                      if (a.status === 'PENDING' && b.status !== 'PENDING') return -1;
                      if (a.status !== 'PENDING' && b.status === 'PENDING') return 1;

                      const sevRank: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
                      const aRank = sevRank[a.severity] || 0;
                      const bRank = sevRank[b.severity] || 0;
                      if (aRank !== bRank) return bRank - aRank;

                      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
                    });

                    return sortedAlerts.map((alert) => (
                      <tr key={alert.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-cyan-400">
                          #ALT-{alert.id}
                        </td>

                      <td className="py-3 px-4">
                        <div className="font-medium text-white">
                          {alert.centre_name || `Centre #${alert.centre_id}`}
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          Session #{alert.monitoring_session_id || alert.session_id} •{' '}
                          {alert.centre_code || ''}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        {alert.alert_type === 'ATTENDANCE_DISCREPANCY' ? (
                          <Badge variant="outline" className="border-cyan-500/30 text-cyan-400 text-[10px]">
                            Attendance Discrepancy
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-purple-500/30 text-purple-400 text-[10px]">
                            Infrastructure Discrepancy
                          </Badge>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            alert.severity === 'HIGH'
                              ? 'danger'
                              : alert.severity === 'MEDIUM'
                              ? 'warning'
                              : 'outline'
                          }
                          className="text-[10px]"
                        >
                          {alert.severity}
                        </Badge>
                      </td>

                      <td className="py-3 px-4">
                        <div className="text-slate-200">
                          {alert.title}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          Expected: {alert.expected_value} | Observed: {alert.observed_value} (Diff:{' '}
                          <span className="text-amber-400">{alert.difference}</span>)
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        {alert.status === 'PENDING' ? (
                          <Badge variant="warning" className="flex items-center gap-1 w-fit">
                            <Clock className="w-3 h-3" /> PENDING
                          </Badge>
                        ) : alert.status === 'VERIFIED' ? (
                          <Badge variant="success" className="flex items-center gap-1 w-fit">
                            <CheckCircle2 className="w-3 h-3" /> VERIFIED
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-slate-400 border-slate-700 flex items-center gap-1 w-fit">
                            <XCircle className="w-3 h-3" /> FALSE POSITIVE
                          </Badge>
                        )}
                      </td>

                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        {alert.evidence ? `${alert.evidence.length} Snapshots` : 'Attached'}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Link href={`/alerts/${alert.id}`}>
                          <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5 ml-auto">
                            <Eye className="w-3.5 h-3.5" />
                            Inspect & Review
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))
                })()}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
