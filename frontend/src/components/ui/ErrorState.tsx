import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '@/lib/utils/cn';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Service Connection Issue',
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'p-8 rounded-xl border border-rose-500/20 bg-rose-500/5 text-center flex flex-col items-center justify-center space-y-3',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-rose-200">{title}</h4>
      <p className="text-sm text-slate-400 max-w-md leading-relaxed">{message}</p>
      {onRetry && (
        <div className="pt-2">
          <Button variant="secondary" size="sm" onClick={onRetry} className="gap-2">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </Button>
        </div>
      )}
    </div>
  );
}
