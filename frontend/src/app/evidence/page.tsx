'use client';

import React from 'react';
import { Shield, Image as ImageIcon } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';

export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence Snapshot Viewer"
        description="Audit archive of timestamped snapshot frames tied to compliance discrepancies, with privacy-preserving face obfuscation."
        badge={<Badge variant="outline">Privacy Preserved</Badge>}
      />

      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-3">
        <Shield className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-emerald-400">Privacy & Transparency Safeguards</p>
          <p className="text-slate-300">
            Monitoring uses aggregate visual counts and does not perform individual identity recognition. Attendance is estimated from periodic visual snapshots using Stithi AI. The system does not identify individuals.
          </p>
          <p className="text-slate-400 text-[11px]">
            Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={ImageIcon}
            title="No Evidence Snapshots Stored Yet"
            description="When monitoring sessions detect an attendance discrepancy exceeding tolerance or potential infrastructure discrepancy, supporting snapshots with bounding box annotations will be displayed here for reviewer audit."
            className="p-16 border-0"
          />
        </CardContent>
      </Card>
    </div>
  );
}
