'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Building2,
  Video,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  RotateCw,
  Clock,
  Activity,
  CheckCircle2,
  Boxes,
  Users,
  Scale,
  Shield,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { dashboardApi } from '@/lib/api/dashboard';
import { alertsApi } from '@/lib/api/alerts';
import {
  DashboardSummary,
  CentreOverviewItem,
  RecentActivityItem,
} from '@/lib/types/dashboard';
import { Alert } from '@/lib/types/alert';
import { AlertDistributionChart } from '@/components/dashboard/AlertDistributionChart';
import { ComplianceDistributionChart } from '@/components/dashboard/ComplianceDistributionChart';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [centresOverview, setCentresOverview] = useState<CentreOverviewItem[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [recentActivity, setRecentActivity] = useState<RecentActivityItem[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  const loadDashboardData = useCallback(async (refreshOnly = false) => {
    if (refreshOnly) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [
        sumData,
        centresData,
        alertsData,
        activityData,
      ] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getCentresOverview(8),
        alertsApi.listAlerts(),
        dashboardApi.getRecentActivity(8),
      ]);

      setSummary(sumData);
      setCentresOverview(centresData);
      setRecentAlerts((alertsData || []).slice(0, 5));
      setRecentActivity(activityData);
      setIsBackendOnline(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to load monitoring data.';
      setError(msg);
      setIsBackendOnline(false);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  if (isLoading) {
    return <LoadingState message="Connecting to secure compliance database..." />;
  }

  if (error && !summary) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="National Skilling Monitoring Dashboard"
          description="Automated AI compliance and evidence audit system."
        />
        <ErrorState
          title="Dashboard Data Unavailable"
          message={error}
          onRetry={() => loadDashboardData()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <PageHeader
          title="AI Training Centre Monitoring Dashboard"
          description="Unified surveillance portal verifying anonymous trainee attendance and sanctioned physical infrastructure across training centres."
          badge={
            isBackendOnline ? (
              <Badge variant="success">FastAPI Connected</Badge>
            ) : (
              <Badge variant="warning">Backend Offline</Badge>
            )
          }
        />
        <div className="flex items-center gap-2 self-start md:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadDashboardData(true)}
            disabled={isRefreshing}
            className="text-xs gap-1.5"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Data'}</span>
          </Button>
          <Link href="/monitoring">
            <Button variant="primary" size="sm" className="text-xs gap-1.5">
              <Video className="w-3.5 h-3.5" />
              <span>Launch Monitoring</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* AI Transparency & Privacy Notice Banner (PRD & SRS Safeguards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
        <div className="flex items-start gap-2.5">
          <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
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
              Infrastructure AI Transparency
            </p>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.
            </p>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards Grid (6 real backend metrics) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Card 1: Centres */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Centres
            </span>
            <Building2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {summary?.centres.total ?? 0}
            </span>
            <span className="text-[10px] text-slate-400">
              ({summary?.centres.active ?? 0} active)
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Registered training centres</p>
        </Card>

        {/* Card 2: Monitoring Sessions */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Sessions
            </span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {summary?.monitoring_sessions.total ?? 0}
            </span>
            <span className="text-[10px] text-emerald-400">
              {summary?.monitoring_sessions.completed ?? 0} done
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">
            {summary?.monitoring_sessions.running ?? 0} running currently
          </p>
        </Card>

        {/* Card 3: Pending Alerts */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Pending Alerts
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-amber-400">
              {summary?.alerts.pending ?? 0}
            </span>
            <span className="text-[10px] text-rose-400">
              {summary?.alerts.high_severity ?? 0} high
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Awaiting human review</p>
        </Card>

        {/* Card 4: Verified Alerts */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Verified
            </span>
            <ShieldCheck className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {summary?.alerts.verified ?? 0}
            </span>
            <span className="text-[10px] text-emerald-400">
              {summary?.alerts.false_positive ?? 0} false+
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Confirmed by human reviewer</p>
        </Card>

        {/* Card 5: Attendance Discrepancies */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Attendance Diff
            </span>
            <Users className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {summary?.compliance.attendance_discrepancies ?? 0}
            </span>
            <span className="text-[10px] text-emerald-400">
              {summary?.compliance.attendance_matches ?? 0} match
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Variance beyond tolerance</p>
        </Card>

        {/* Card 6: Infrastructure Discrepancies */}
        <Card className="p-3.5 bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Infra Diff
            </span>
            <Scale className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {summary?.compliance.infrastructure_discrepancies ?? 0}
            </span>
            <span className="text-[10px] text-emerald-400">
              {summary?.compliance.infrastructure_compliant ?? 0} ok
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Below sanctioned baseline</p>
        </Card>
      </div>

      {/* Compliance & Alert Charts (Recharts) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {summary && <AlertDistributionChart alerts={summary.alerts} />}
        {summary && <ComplianceDistributionChart compliance={summary.compliance} />}
      </div>

      {/* Monitoring Overview Table (Centres Overview) */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Training Centres Operational Status</CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Live status, latest monitoring runs, and compliance health across registered centres
            </p>
          </div>
          <Link href="/centres">
            <Button variant="outline" size="sm" className="text-xs gap-1">
              <span>All Centres</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {centresOverview.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/50 border-b border-slate-800 text-slate-400 uppercase font-mono tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Centre</th>
                    <th className="px-4 py-3">Cameras</th>
                    <th className="px-4 py-3">Latest Session</th>
                    <th className="px-4 py-3">Session Status</th>
                    <th className="px-4 py-3">Attendance</th>
                    <th className="px-4 py-3">Infrastructure</th>
                    <th className="px-4 py-3">Pending Alerts</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {centresOverview.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-200">{c.name}</div>
                        <div className="text-[11px] font-mono text-slate-400">
                          {c.centre_code} {c.location ? `• ${c.location}` : ''}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-300">
                        {c.camera_count}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-300">
                        {c.latest_session_id ? (
                          <Link
                            href={`/monitoring`}
                            className="hover:text-emerald-400 underline underline-offset-2"
                          >
                            Session #{c.latest_session_id}
                          </Link>
                        ) : (
                          <span className="text-slate-500">None yet</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.latest_session_status ? (
                          <Badge
                            variant={
                              c.latest_session_status === 'COMPLETED'
                                ? 'success'
                                : c.latest_session_status === 'RUNNING'
                                ? 'default'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {c.latest_session_status}
                          </Badge>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.latest_attendance_compliance ? (
                          <Badge
                            variant={
                              c.latest_attendance_compliance === 'MATCH'
                                ? 'success'
                                : c.latest_attendance_compliance === 'DISCREPANCY'
                                ? 'danger'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {c.latest_attendance_compliance}
                          </Badge>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.latest_infrastructure_compliance ? (
                          <Badge
                            variant={
                              c.latest_infrastructure_compliance === 'COMPLIANT'
                                ? 'success'
                                : c.latest_infrastructure_compliance === 'DISCREPANCY'
                                ? 'danger'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {c.latest_infrastructure_compliance}
                          </Badge>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.pending_alerts_count > 0 ? (
                          <Badge variant="warning" className="text-[10px] font-mono">
                            {c.pending_alerts_count} PENDING
                          </Badge>
                        ) : (
                          <span className="text-slate-500">0</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/centres/${c.id}`}>
                          <Button variant="ghost" size="sm" className="text-xs h-7 px-2">
                            <span>Inspect</span>
                            <ArrowRight className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={Building2}
              title="No Centres Configured Yet"
              description="Register training centres in the system to begin continuous automated surveillance."
              className="py-12"
            />
          )}
        </CardContent>
      </Card>

      {/* Two-Column Bottom Grid: Recent Alerts & Recent Sessions / Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Recent Discrepancy Alerts */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Recent Compliance Alerts</span>
              </CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">
                Evidence-backed discrepancy records requiring human verification
              </p>
            </div>
            <Link href="/alerts">
              <Button variant="outline" size="sm" className="text-xs gap-1">
                <span>All Alerts</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0 flex-1">
            {recentAlerts.length > 0 ? (
              <div className="divide-y divide-slate-800/60 text-xs">
                {recentAlerts.map((alert) => (
                  <Link
                    key={alert.id}
                    href={`/alerts/${alert.id}`}
                    className="flex items-center justify-between p-3.5 hover:bg-slate-800/40 transition-colors"
                  >
                    <div className="space-y-1 min-w-0 pr-3">
                      <div className="flex items-center gap-2">
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
                        <span className="font-semibold text-slate-200 truncate">
                          {alert.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate">
                        {alert.description || `Expected ${alert.expected_value}, observed ${alert.observed_value}`}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <Badge
                        variant={
                          alert.status === 'VERIFIED'
                            ? 'danger'
                            : alert.status === 'FALSE_POSITIVE'
                            ? 'success'
                            : 'warning'
                        }
                        className="text-[10px]"
                      >
                        {alert.status}
                      </Badge>
                      <p className="text-[10px] text-slate-500 font-mono mt-1">
                        #{alert.id}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={ShieldCheck}
                title="No Compliance Alerts Found"
                description="When AI compliance detects discrepancies beyond tolerance, traceable alerts with supporting CCTV snapshots will appear here."
                className="py-10 border-0"
              />
            )}
          </CardContent>
        </Card>

        {/* Right: Live Audit & Activity Timeline */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <span>Live Audit Activity</span>
              </CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">
                Real database operation timeline of sessions and reviewer actions
              </p>
            </div>
            <Link href="/monitoring">
              <Button variant="outline" size="sm" className="text-xs gap-1">
                <span>Sessions</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0 flex-1">
            {recentActivity.length > 0 ? (
              <div className="divide-y divide-slate-800/60 text-xs">
                {recentActivity.map((event) => (
                  <div
                    key={event.id}
                    className="p-3.5 flex items-start gap-3 hover:bg-slate-800/20 transition-colors"
                  >
                    <div className="mt-0.5 shrink-0">
                      {event.activity_type.includes('COMPLETED') ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : event.activity_type.includes('VERIFIED') ? (
                        <ShieldAlert className="w-4 h-4 text-rose-400" />
                      ) : event.activity_type.includes('FALSE_POSITIVE') ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Activity className="w-4 h-4 text-blue-400" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-semibold text-slate-200 truncate">
                          {event.title}
                        </p>
                        <span className="text-[10px] font-mono text-slate-500 shrink-0">
                          {new Date(event.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {event.description}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-500">
                        <span className="font-medium text-slate-400">
                          {event.centre_name} ({event.centre_code})
                        </span>
                        {event.alert_id && (
                          <Link
                            href={`/alerts/${event.alert_id}`}
                            className="text-emerald-400 hover:underline"
                          >
                            View Alert →
                          </Link>
                        )}
                        {event.session_id && !event.alert_id && (
                          <Link
                            href={`/monitoring`}
                            className="text-blue-400 hover:underline"
                          >
                            View Session →
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Clock}
                title="No Activity Logged Yet"
                description="Chronological session executions and reviewer decisions will be audited here."
                className="py-10 border-0"
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
