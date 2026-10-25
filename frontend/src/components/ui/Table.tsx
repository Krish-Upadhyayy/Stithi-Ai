import React from 'react';
import { cn } from '@/lib/utils/cn';

export function Table({ className, children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-auto">
      <table className={cn('w-full caption-bottom text-sm text-left', className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn('[&_tr]:border-b border-slate-800 text-xs text-slate-400 bg-slate-900/60', className)} {...props}>
      {children}
    </thead>
  );
}

export function TableBody({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn('[&_tr:last-child]:border-0', className)} {...props}>
      {children}
    </tbody>
  );
}

export function TableRow({ className, children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        'border-b border-slate-800/60 transition-colors hover:bg-slate-800/40 data-[state=selected]:bg-slate-800',
        className
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export function TableHead({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn('h-10 px-4 text-left align-middle font-medium text-slate-400 uppercase tracking-wider text-[11px]', className)}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ className, children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn('p-4 align-middle text-slate-200', className)} {...props}>
      {children}
    </td>
  );
}
