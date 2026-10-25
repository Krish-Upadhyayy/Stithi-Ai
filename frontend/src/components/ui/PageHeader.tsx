import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  action,
  badge,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800/80',
        className
      )}
    >
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
          {badge}
        </div>
        {description && (
          <p className="text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
    </div>
  );
}
