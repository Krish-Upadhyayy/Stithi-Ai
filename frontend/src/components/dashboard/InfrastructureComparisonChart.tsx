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
import { Boxes } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { InfrastructureComplianceItem } from '@/lib/types/monitoring';

interface InfrastructureComparisonChartProps {
  items: InfrastructureComplianceItem[];
}

export function InfrastructureComparisonChart({ items }: InfrastructureComparisonChartProps) {
  const monitoredItems = items.filter((i) => i.status !== 'NOT_MONITORED');
  const hasData = monitoredItems.length > 0;

  const data = monitoredItems.map((item) => ({
    name: item.item_name.length > 15 ? `${item.item_name.slice(0, 14)}…` : item.item_name,
    fullName: item.item_name,
    Expected: item.expected_quantity,
    'Observed (AI)': item.observed_quantity ?? 0,
    Difference: item.difference ?? 0,
    status: item.status,
  }));

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-200">
              Sanctioned Infrastructure Baseline vs AI Observations
            </CardTitle>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Apparent visual detections compared against inventory allocation records
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {monitoredItems.length} Monitored Items
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center items-center min-h-[220px]">
        {hasData ? (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 10, right: 20, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.5rem',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                  formatter={(val: unknown, name: unknown, item: unknown) => {
                    const row = item as { payload?: { fullName?: string } };
                    return [
                      String(val ?? 0),
                      `${String(name)} (${row.payload?.fullName || name})`,
                    ];
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={30}
                  formatter={(val: string) => (
                    <span className="text-xs text-slate-300 font-medium ml-1">
                      {val}
                    </span>
                  )}
                />
                <Bar
                  dataKey="Expected"
                  fill="#38bdf8"
                  radius={[0, 4, 4, 0]}
                  barSize={12}
                />
                <Bar
                  dataKey="Observed (AI)"
                  fill="#10b981"
                  radius={[0, 4, 4, 0]}
                  barSize={12}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            icon={Boxes}
            title="No Monitored Equipment"
            description="Upload sanctioned inventory baselines and run infrastructure AI to compare visual detections."
            className="py-6 border-0"
          />
        )}
      </CardContent>
    </Card>
  );
}
