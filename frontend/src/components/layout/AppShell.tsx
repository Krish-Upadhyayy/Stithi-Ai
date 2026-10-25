'use client';

import React, { Suspense, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { LoadingState } from '@/components/ui/LoadingState';

function AppShellContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const isLoginPage = pathname === '/login';

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isLoginPage) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, isLoginPage, router]);

  // For the login page, render child component without internal layout shell
  if (isLoginPage) {
    return <main className="min-h-screen w-screen bg-slate-950">{children}</main>;
  }

  // When validating token on initial load
  if (isLoading) {
    return (
      <div className="min-h-screen w-screen bg-slate-950 flex items-center justify-center">
        <LoadingState message="Validating authentication session..." />
      </div>
    );
  }

  // If unauthenticated on protected route
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen w-screen bg-slate-950 flex items-center justify-center">
        <LoadingState message="Redirecting to login..." />
      </div>
    );
  }

  // Authenticated user inside application shell
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      <Suspense fallback={<div className="w-64 bg-slate-900 border-r border-slate-800" />}>
        <Sidebar />
      </Suspense>
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            <Suspense fallback={<div className="p-8 text-center text-slate-500">Loading view...</div>}>
              {children}
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-screen bg-slate-950 flex items-center justify-center">
          <LoadingState message="Initializing system..." />
        </div>
      }
    >
      <AppShellContent>{children}</AppShellContent>
    </Suspense>
  );
}
