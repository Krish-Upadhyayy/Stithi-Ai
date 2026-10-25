'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Building2,
  Plus,
  Search,
  ExternalLink,
  Camera as CameraIcon,
  CheckCircle2,
  AlertCircle,
  PowerOff,
  Power,
  RotateCw,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { LoadingState } from '@/components/ui/LoadingState';
import { centresApi } from '@/lib/api/centres';
import { dashboardApi } from '@/lib/api/dashboard';
import { Centre, CentreStatus } from '@/lib/types/centre';
import { CentreOverviewItem } from '@/lib/types/dashboard';
import { useAuth } from '@/lib/auth/auth-context';

export default function CentresPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const [centres, setCentres] = useState<Centre[]>([]);
  const [centresOverview, setCentresOverview] = useState<Record<number, CentreOverviewItem>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [monitoringFilter, setMonitoringFilter] = useState<string>('ALL');

  // Create Centre Modal state
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [centreCode, setCentreCode] = useState<string>('');
  const [centreName, setCentreName] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [status, setStatus] = useState<CentreStatus>('ACTIVE');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchCentres = useCallback(async () => {
    setError(null);
    try {
      const [data, overviewData] = await Promise.all([
        centresApi.getCentres(),
        dashboardApi.getCentresOverview().catch(() => [] as CentreOverviewItem[]),
      ]);
      setCentres(data);
      const overviewMap: Record<number, CentreOverviewItem> = {};
      overviewData.forEach((item) => {
        overviewMap[item.id] = item;
      });
      setCentresOverview(overviewMap);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve training centres.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    centresApi
      .getCentres()
      .then((data) => {
        if (isMounted) setCentres(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to retrieve training centres.';
          setError(msg);
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleOpenModal = () => {
    setCentreCode('');
    setCentreName('');
    setLocation('');
    setStatus('ACTIVE');
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleCreateCentre = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const trimmedCode = centreCode.trim();
    const trimmedName = centreName.trim();

    if (!trimmedCode) {
      setFormError('Centre code is required (e.g. TC-DL-001).');
      return;
    }
    if (trimmedCode.length < 2) {
      setFormError('Centre code must be at least 2 characters.');
      return;
    }
    if (!trimmedName) {
      setFormError('Centre name is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await centresApi.createCentre({
        centre_code: trimmedCode,
        name: trimmedName,
        location: location.trim() || null,
        status,
      });

      setCentres((prev) => [...prev, created]);
      setIsModalOpen(false);
      setSuccessMessage(`Successfully registered ${created.name} (${created.centre_code})`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to create centre.';
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (centre: Centre) => {
    if (!isAdmin) return;
    const newStatus: CentreStatus = centre.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    const actionText = newStatus === 'ACTIVE' ? 'activate' : 'deactivate';

    if (!confirm(`Are you sure you want to ${actionText} centre "${centre.name}"?`)) {
      return;
    }

    try {
      const updated = await centresApi.updateCentreStatus(centre.id, newStatus);
      setCentres((prev) =>
        prev.map((c) => (c.id === updated.id ? { ...c, status: updated.status } : c))
      );
      setSuccessMessage(`Centre "${centre.name}" is now ${newStatus}.`);
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update status.';
      alert(msg);
    }
  };

  const filteredCentres = centres.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.centre_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.location && c.location.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' || c.status === statusFilter;

    const overview = centresOverview[c.id];
    const matchesMonitoring =
      monitoringFilter === 'ALL' ||
      (monitoringFilter === 'WITH_SESSIONS' && overview?.latest_session_id) ||
      (monitoringFilter === 'PENDING_ALERTS' && overview && overview.pending_alerts_count > 0) ||
      (monitoringFilter === 'COMPLETED' && overview?.latest_session_status === 'COMPLETED') ||
      (monitoringFilter === 'NO_SESSIONS' && !overview?.latest_session_id);

    return matchesSearch && matchesStatus && matchesMonitoring;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Training Centres"
        description="Official registry of accredited skilling centres, linked camera feeds, and automated presence monitoring."
        action={
          isAdmin ? (
            <Button onClick={handleOpenModal} className="gap-2 text-sm bg-emerald-600 hover:bg-emerald-500 text-white">
              <Plus className="w-4 h-4" />
              <span>Register Centre</span>
            </Button>
          ) : undefined
        }
      />

      {/* Success Notification Alert */}
      {successMessage && (
        <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
            ×
          </button>
        </div>
      )}

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800">
        <div className="flex items-center gap-2 flex-1">
          <Search className="w-4 h-4 text-slate-500 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by centre code, name, or location..."
            className="bg-transparent text-sm text-slate-200 placeholder:text-slate-500 outline-none w-full"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 border-t sm:border-t-0 sm:border-l border-slate-800 pt-2 sm:pt-0 sm:pl-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter centres by operational status"
            className="bg-slate-800 border border-slate-700 text-xs text-slate-300 rounded px-2.5 py-1.5 outline-none"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
            <option value="SUSPENDED">Suspended</option>
          </select>

          <select
            value={monitoringFilter}
            onChange={(e) => setMonitoringFilter(e.target.value)}
            aria-label="Filter centres by monitoring status"
            className="bg-slate-800 border border-slate-700 text-xs text-slate-300 rounded px-2.5 py-1.5 outline-none"
          >
            <option value="ALL">All Monitoring</option>
            <option value="WITH_SESSIONS">Has Sessions</option>
            <option value="PENDING_ALERTS">Has Pending Alerts</option>
            <option value="COMPLETED">Latest Completed</option>
            <option value="NO_SESSIONS">No Sessions Yet</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <Card>
          <CardContent className="p-12">
            <LoadingState message="Loading registered training centres..." />
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-8">
            <ErrorState
              title="Failed to Load Centres"
              message={error}
              onRetry={fetchCentres}
            />
          </CardContent>
        </Card>
      ) : filteredCentres.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-800">
              {filteredCentres.map((centre) => {
                const isActive = centre.status === 'ACTIVE';
                const overview = centresOverview[centre.id];
                return (
                  <div
                    key={centre.id}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/40 transition-colors"
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2.5">
                        <span className="font-semibold text-white text-base">{centre.name}</span>
                        <Badge variant="outline" className="font-mono text-xs text-slate-300 border-slate-700">
                          {centre.centre_code}
                        </Badge>
                        <Badge variant={isActive ? 'success' : 'danger'}>
                          {centre.status}
                        </Badge>
                        <span className="inline-flex items-center gap-1 text-xs text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700/50">
                          <CameraIcon className="w-3 h-3 text-slate-400" />
                          <span>{centre.camera_count} {centre.camera_count === 1 ? 'Camera' : 'Cameras'}</span>
                        </span>
                        {overview?.latest_session_status && (
                          <Badge
                            variant={
                              overview.latest_session_status === 'COMPLETED'
                                ? 'success'
                                : overview.latest_session_status === 'RUNNING'
                                ? 'default'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            Session: {overview.latest_session_status}
                          </Badge>
                        )}
                        {overview && overview.pending_alerts_count > 0 && (
                          <Badge variant="warning" className="text-[10px] font-mono">
                            {overview.pending_alerts_count} Pending Alert{overview.pending_alerts_count > 1 ? 's' : ''}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">
                        {centre.location || 'Location details not specified'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      {isAdmin && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleStatus(centre)}
                          title={isActive ? 'Deactivate centre' : 'Activate centre'}
                          className={`text-xs gap-1.5 ${
                            isActive
                              ? 'text-slate-400 hover:text-rose-400 hover:bg-rose-500/10'
                              : 'text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10'
                          }`}
                        >
                          {isActive ? (
                            <>
                              <PowerOff className="w-3.5 h-3.5 text-rose-400" />
                              <span className="hidden md:inline">Deactivate</span>
                            </>
                          ) : (
                            <>
                              <Power className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="hidden md:inline">Activate</span>
                            </>
                          )}
                        </Button>
                      )}

                      <Link href={`/centres/${centre.id}`}>
                        <Button variant="outline" size="sm" className="text-xs gap-1.5 border-slate-700 hover:border-slate-600">
                          <span>View Centre</span>
                          <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : searchQuery ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <Building2 className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-sm text-slate-300 font-medium">No centres matching &quot;{searchQuery}&quot;</p>
            <p className="text-xs text-slate-500">Try modifying your search terms or clearing the filter.</p>
            <Button variant="outline" size="sm" onClick={() => setSearchQuery('')} className="text-xs">
              Clear Filter
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Building2}
              title="No Training Centres Registered Yet"
              description="Register training centres to configure camera feeds, bind operational locations, and establish monitoring compliance baselines."
              action={
                isAdmin ? (
                  <Button onClick={handleOpenModal} className="gap-2 text-sm bg-emerald-600 hover:bg-emerald-500 text-white">
                    <Plus className="w-4 h-4" />
                    <span>Register First Centre</span>
                  </Button>
                ) : undefined
              }
            />
          </CardContent>
        </Card>
      )}

      {/* Register Centre Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => !isSubmitting && setIsModalOpen(false)}
        title="Register New Training Centre"
        description="Enter the training centre identifier, official name, and location details."
      >
        <form onSubmit={handleCreateCentre} className="space-y-4 pt-2">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Centre Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={centreCode}
              onChange={(e) => setCentreCode(e.target.value.toUpperCase())}
              placeholder="e.g. TC-DL-001"
              disabled={isSubmitting}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-mono uppercase"
            />
            <p className="text-[11px] text-slate-500 mt-1">Unique government identifier for this facility.</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Centre Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={centreName}
              onChange={(e) => setCentreName(e.target.value)}
              placeholder="e.g. Delhi Skill Development Hub"
              disabled={isSubmitting}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Location / Address
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Sector 12, Dwarka, New Delhi"
              disabled={isSubmitting}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Initial Operational Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as CentreStatus)}
              disabled={isSubmitting}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="ACTIVE">ACTIVE — Facility operating and eligible for monitoring</option>
              <option value="INACTIVE">INACTIVE — Facility temporarily inactive</option>
              <option value="SUSPENDED">SUSPENDED — Facility under compliance audit</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[110px]"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-1.5">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </span>
              ) : (
                'Create Centre'
              )}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
