import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'p-12 rounded-xl border border-dashed border-slate-800 bg-slate-900/40 text-center flex flex-col items-center justify-center space-y-3',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-white">{title}</h4>
      <p className="text-sm text-slate-400 max-w-md leading-relaxed">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}
