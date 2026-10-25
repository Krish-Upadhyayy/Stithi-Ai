import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = 'Loading data...', className }: LoadingStateProps) {
  return (
    <div className={cn('p-12 flex flex-col items-center justify-center text-center space-y-3', className)}>
      <Loader2 className="w-7 h-7 text-emerald-400 animate-spin" />
      <p className="text-sm font-medium text-slate-300">{message}</p>
      <p className="text-xs text-slate-500">Querying backend service...</p>
    </div>
  );
}
