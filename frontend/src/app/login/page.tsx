'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Lock, Mail, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth/auth-context';
import { Button } from '@/components/ui/Button';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      router.replace('/');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Authentication failed. Please check your credentials.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-950 text-slate-100">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-2">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">AI Training Centre Monitoring System</h1>
          <p className="text-xs text-slate-400">
            Government Skilling Compliance & Verification Portal
          </p>
        </div>

        {/* Login Form Box */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 shadow-xl space-y-6">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-white">Account Login</h2>
            <p className="text-xs text-slate-400">
              Enter your authorized email and password to access the monitoring dashboard.
            </p>
          </div>

          {error && (
            <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5 animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-sm">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@sih.gov.in"
                  disabled={isSubmitting}
                  className="w-full bg-slate-800/80 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-slate-200 placeholder:text-slate-500 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={isSubmitting}
                  className="w-full bg-slate-800/80 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-slate-200 placeholder:text-slate-500 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="w-full py-2.5 text-sm mt-2"
            >
              Sign In to System
            </Button>
          </form>

          <div className="pt-2 border-t border-slate-800 text-center">
            <p className="text-[11px] text-slate-500">
              Development Admin: <code className="text-slate-400 font-mono">admin@sih.gov.in</code> (configured via seed utility)
            </p>
          </div>
        </div>

        {/* Security / Privacy Disclosure */}
        <div className="text-center text-xs text-slate-500 space-y-1">
          <p>Protected by Token-Based Authentication</p>
          <p className="text-[11px] text-slate-600">Privacy Safeguard: Anonymous counts only. No facial recognition identity tracking.</p>
        </div>
      </div>
    </div>
  );
}
