'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Scale } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { DashboardComplianceSummary } from '@/lib/types/dashboard';

interface ComplianceDistributionChartProps {
  compliance: DashboardComplianceSummary;
}

export function ComplianceDistributionChart({ compliance }: ComplianceDistributionChartProps) {
  const attendanceTotal =
    compliance.attendance_matches +
    compliance.attendance_discrepancies +
    compliance.attendance_insufficient_data;

  const infrastructureTotal =
    compliance.infrastructure_compliant +
    compliance.infrastructure_discrepancies +
    compliance.infrastructure_insufficient_data +
    compliance.infrastructure_not_monitored;

  const hasData = attendanceTotal > 0 || infrastructureTotal > 0;

  const data = [
    {
      category: 'Attendance',
      Match: compliance.attendance_matches,
      Discrepancy: compliance.attendance_discrepancies,
      'Insufficient Data': compliance.attendance_insufficient_data,
    },
    {
      category: 'Infrastructure',
      Match: compliance.infrastructure_compliant,
      Discrepancy: compliance.infrastructure_discrepancies,
      'Insufficient Data': compliance.infrastructure_insufficient_data,
    },
  ];

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-slate-200">
            Compliance Evaluation Distribution
          </CardTitle>
          <span className="text-xs font-mono text-slate-400">
            {attendanceTotal} Attendance / {infrastructureTotal} Equipment
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center items-center min-h-[220px]">
        {hasData ? (
          <div className="w-full h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis
                  dataKey="category"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.5rem',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value: string) => (
                    <span className="text-xs text-slate-300 font-medium ml-1">
                      {value}
                    </span>
                  )}
                />
                <Bar dataKey="Match" name="Compliant / Match" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Discrepancy" name="Discrepancy" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar
                  dataKey="Insufficient Data"
                  name="Insufficient Data"
                  fill="#64748b"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            icon={Scale}
            title="No Compliance Records"
            description="Run compliance calculations on monitoring sessions to view empirical alignment comparisons."
            className="py-6 border-0"
          />
        )}
      </CardContent>
    </Card>
  );
}
