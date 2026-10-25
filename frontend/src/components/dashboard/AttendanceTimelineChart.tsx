'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Users } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { AttendanceObservation } from '@/lib/types/monitoring';

interface AttendanceTimelineChartProps {
  observations: AttendanceObservation[];
  physicalAttendance?: number | null;
  aiEstimatedAttendance?: number | null;
  tolerance?: number;
}

export function AttendanceTimelineChart({
  observations,
  physicalAttendance,
  aiEstimatedAttendance,
  tolerance = 2,
}: AttendanceTimelineChartProps) {
  const validObservations = observations.filter(
    (o) => o.processing_status === 'COMPLETED'
  );

  const hasData = validObservations.length > 0;

  const chartData = validObservations.map((obs, idx) => ({
    frame: `Snap #${obs.snapshot_id ?? idx + 1}`,
    count: obs.detected_count ?? 0,
    confidence: obs.confidence_score ? Math.round(obs.confidence_score * 100) : (obs.max_confidence ? Math.round(obs.max_confidence * 100) : null),
    timestamp: obs.created_at ? new Date(obs.created_at).toLocaleTimeString() : `F${idx + 1}`,
  }));

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-slate-200">
              Attendance Observation Timeline
            </CardTitle>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Headcount variation observed by Stithi AI across periodic snapshot frames
            </p>
          </div>
          {aiEstimatedAttendance !== undefined && aiEstimatedAttendance !== null && (
            <div className="text-right">
              <span className="text-xs text-slate-400">AI Estimate: </span>
              <span className="text-xs font-semibold font-mono text-emerald-400">
                {aiEstimatedAttendance.toFixed(1)}
              </span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-center items-center min-h-[220px]">
        {hasData ? (
          <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 15, right: 20, left: -20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis
                  dataKey="frame"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.5rem',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                  formatter={(val: unknown, name: unknown) => [
                    String(val ?? 0),
                    name === 'count' ? 'Detected Headcount' : String(name),
                  ]}
                />
                <Legend
                  verticalAlign="bottom"
                  height={30}
                  formatter={(val: string) => (
                    <span className="text-xs text-slate-300 font-medium ml-1">
                      {val === 'count' ? 'Stithi AI Detected Count' : val}
                    </span>
                  )}
                />
                {physicalAttendance !== undefined && physicalAttendance !== null && (
                  <ReferenceLine
                    y={physicalAttendance}
                    label={{
                      value: `Physical: ${physicalAttendance}`,
                      fill: '#38bdf8',
                      fontSize: 10,
                      position: 'top',
                    }}
                    stroke="#38bdf8"
                    strokeDasharray="4 4"
                  />
                )}
                {physicalAttendance !== undefined &&
                  physicalAttendance !== null &&
                  tolerance > 0 && (
                    <>
                      <ReferenceLine
                        y={physicalAttendance + tolerance}
                        stroke="#64748b"
                        strokeDasharray="2 2"
                        opacity={0.6}
                      />
                      <ReferenceLine
                        y={Math.max(0, physicalAttendance - tolerance)}
                        stroke="#64748b"
                        strokeDasharray="2 2"
                        opacity={0.6}
                      />
                    </>
                  )}
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#10b981' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            icon={Users}
            title="No Attendance Observations Available"
            description="Process attendance frames for this session using Stithi AI to visualize headcount consistency across time."
            className="py-6 border-0"
          />
        )}
      </CardContent>
    </Card>
  );
}
