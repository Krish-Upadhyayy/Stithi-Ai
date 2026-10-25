'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Activity, Bell, Server, RefreshCw } from 'lucide-react';
import { healthApi } from '@/lib/api/health';
import { HealthStatus } from '@/lib/types/health';
import { Badge } from '@/components/ui/Badge';

export function Navbar() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await healthApi.getHealth();
      setHealth(data);
      setIsError(false);
    } catch {
      setIsError(true);
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  }, []);

  const handleManualRefresh = () => {
    setIsChecking(true);
    fetchHealth();
  };

  useEffect(() => {
    let isMounted = true;
    healthApi
      .getHealth()
      .then((data) => {
        if (isMounted) {
          setHealth(data);
          setIsError(false);
          setIsChecking(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsError(true);
          setHealth(null);
          setIsChecking(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/30">
          Stithi AI
        </span>
        <span className="text-xs text-slate-400 hidden sm:inline">
          Training Centre Compliance & Attendance Monitoring
        </span>
      </div>

      <div className="flex items-center gap-3 text-xs">
        {/* Real Backend Status Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-300 font-medium">Backend API:</span>
          {isChecking ? (
            <Badge variant="default" className="text-[10px]">Checking...</Badge>
          ) : isError ? (
            <Badge variant="warning" className="text-[10px]">Offline / Unreachable</Badge>
          ) : (
            <Badge variant="success" className="text-[10px]">
              Connected ({health?.version || 'v0.2.0'})
            </Badge>
          )}
          <button
            onClick={handleManualRefresh}
            title="Refresh backend status"
            disabled={isChecking}
            className="text-slate-400 hover:text-slate-200 transition-colors ml-1 p-0.5 rounded hover:bg-slate-700"
          >
            <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* AI Pipelines Stage Badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
          <Activity className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-slate-300 font-medium">AI Pipelines:</span>
          <Badge variant="outline" className="text-[10px]">Decoupled (Staged)</Badge>
        </div>

        <div className="p-2 rounded-lg bg-slate-800/80 text-slate-400 border border-slate-700/60 hover:text-white cursor-pointer transition-colors">
          <Bell className="w-4 h-4" />
        </div>
      </div>
    </header>
  );
}
