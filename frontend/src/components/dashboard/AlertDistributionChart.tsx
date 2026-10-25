'use client';

import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { ShieldAlert } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { DashboardAlertsSummary } from '@/lib/types/dashboard';

interface AlertDistributionChartProps {
  alerts: DashboardAlertsSummary;
}

const COLORS: Record<string, string> = {
  Pending: '#f59e0b',       // Amber
  Verified: '#ef4444',      // Red / Rose
  'False Positive': '#10b981', // Emerald / Green
};

export function AlertDistributionChart({ alerts }: AlertDistributionChartProps) {
  const data = [
    { name: 'Pending', value: alerts.pending },
    { name: 'Verified', value: alerts.verified },
    { name: 'False Positive', value: alerts.false_positive },
  ].filter((d) => d.value > 0);

  const hasData = alerts.total > 0 && data.length > 0;

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-slate-200">
            Alert Resolution Breakdown
          </CardTitle>
          <span className="text-xs font-mono text-slate-400">
            {alerts.total} Total
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center items-center min-h-[220px]">
        {hasData ? (
          <div className="w-full h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {data.map((entry) => (
                    <Cell
                      key={`cell-${entry.name}`}
                      fill={COLORS[entry.name] || '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.5rem',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value: string, entry: unknown) => {
                    const item = entry as { payload?: { value?: number } };
                    return (
                      <span className="text-xs text-slate-300 font-medium ml-1">
                        {value} ({item.payload?.value ?? 0})
                      </span>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            icon={ShieldAlert}
            title="No Alerts Generated"
            description="When compliance discrepancies occur, pending review alerts will be categorized here."
            className="py-6 border-0"
          />
        )}
      </CardContent>
    </Card>
  );
}
