'use client';

import React, { useEffect, useState } from 'react';
import { Building2, Activity, Users, Boxes, Scale } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { monitoringApi } from '@/lib/api/monitoring';
import { centresApi } from '@/lib/api/centres';
import { ComplianceDashboardSummary } from '@/lib/types/monitoring';

interface MetricItem {
  label: string;
  count: number | null;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  statusBadge: React.ReactNode;
}

export function DashboardMetrics() {
  const [summary, setSummary] = useState<ComplianceDashboardSummary | null>(null);
  const [centreCount, setCentreCount] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    centresApi
      .getCentres()
      .then((c) => {
        if (active) setCentreCount(c.length);
      })
      .catch(() => {});

    monitoringApi
      .getComplianceDashboardSummary()
      .then((s) => {
        if (active) setSummary(s);
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  const metrics: MetricItem[] = [
    {
      label: 'Registered Centres',
      count: centreCount,
      description: 'Active skilling centre registries',
      icon: Building2,
      statusBadge:
        centreCount !== null ? (
          <Badge variant="outline">{centreCount} in registry</Badge>
        ) : (
          <Badge variant="outline">Awaiting DB Data</Badge>
        ),
    },
    {
      label: 'Evaluated Sessions',
      count: summary?.total_sessions_evaluated ?? null,
      description: 'Sessions with compliance calculations',
      icon: Activity,
      statusBadge:
        summary !== null ? (
          <Badge variant="default">{summary.total_sessions_evaluated} evaluated</Badge>
        ) : (
          <Badge variant="default">0 evaluated</Badge>
        ),
    },
    {
      label: 'Attendance Matches',
      count: summary?.attendance_matches ?? null,
      description: 'AI headcount within tolerance',
      icon: Users,
      statusBadge:
        summary !== null && summary.attendance_matches > 0 ? (
          <Badge variant="success">{summary.attendance_matches} matches</Badge>
        ) : (
          <Badge variant="outline">0 matches</Badge>
        ),
    },
    {
      label: 'Attendance Discrepancies',
      count: summary?.attendance_discrepancies ?? null,
      description: 'Variance exceeds allowed tolerance',
      icon: Scale,
      statusBadge:
        summary !== null && summary.attendance_discrepancies > 0 ? (
          <Badge variant="warning">{summary.attendance_discrepancies} discrepancies</Badge>
        ) : (
          <Badge variant="outline">0 discrepancies</Badge>
        ),
    },
    {
      label: 'Infrastructure Discrepancies',
      count: summary?.infrastructure_discrepancies ?? null,
      description: 'Observed below expected baseline',
      icon: Boxes,
      statusBadge:
        summary !== null && summary.infrastructure_discrepancies > 0 ? (
          <Badge variant="warning">{summary.infrastructure_discrepancies} items</Badge>
        ) : (
          <Badge variant="outline">0 discrepancies</Badge>
        ),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {metrics.map((m) => {
        const Icon = m.icon;
        return (
          <Card key={m.label} className="p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                {m.label}
              </span>
              <Icon className="w-4 h-4 text-slate-400" />
            </div>

            <div className="my-3">
              <span className="text-2xl font-bold text-white tracking-tight">
                {m.count !== null ? m.count : '--'}
              </span>
              <div className="mt-1.5">{m.statusBadge}</div>
            </div>

            <p className="text-[11px] text-slate-500">{m.description}</p>
          </Card>
        );
      })}
    </div>
  );
}
