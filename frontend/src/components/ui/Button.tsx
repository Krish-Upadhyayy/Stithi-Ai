import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      ...props
    },
    ref
  ) => {
    const variants = {
      primary: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm',
      secondary: 'bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700',
      outline: 'bg-transparent hover:bg-slate-800 text-slate-300 border border-slate-700',
      danger: 'bg-rose-600 hover:bg-rose-500 text-white shadow-sm',
      ghost: 'bg-transparent hover:bg-slate-800/60 text-slate-400 hover:text-slate-200',
    };

    const sizes = {
      sm: 'px-2.5 py-1.5 text-xs rounded-md',
      md: 'px-3.5 py-2 text-sm rounded-lg',
      lg: 'px-4.5 py-2.5 text-base rounded-lg',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed select-none gap-2',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin shrink-0" />
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
