'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Camera as CameraIcon,
  FileSpreadsheet,
  AlertTriangle,
  Clock,
  Plus,
  Edit2,
  Power,
  PowerOff,
  CheckCircle2,
  AlertCircle,
  RotateCw,
  Activity,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingState } from '@/components/ui/LoadingState';
import { Modal } from '@/components/ui/Modal';
import { centresApi } from '@/lib/api/centres';
import { inventoryApi } from '@/lib/api/inventory';
import { monitoringApi } from '@/lib/api/monitoring';
import { alertsApi } from '@/lib/api/alerts';
import {
  Centre,
  CentreStatus,
  Camera,
  CameraSourceType,
} from '@/lib/types/centre';
import { InventoryItem } from '@/lib/types/inventory';
import { MonitoringSession } from '@/lib/types/monitoring';
import { Alert } from '@/lib/types/alert';
import { useAuth } from '@/lib/auth/auth-context';

export default function CentreDetailsPage() {
  const params = useParams();
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const rawId = params?.id;
  const centreId = Number(Array.isArray(rawId) ? rawId[0] : rawId);

  const [centre, setCentre] = useState<Centre | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [sessions, setSessions] = useState<MonitoringSession[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Edit Centre Modal state
  const [isEditCentreOpen, setIsEditCentreOpen] = useState<boolean>(false);
  const [editName, setEditName] = useState<string>('');
  const [editLocation, setEditLocation] = useState<string>('');
  const [editStatus, setEditStatus] = useState<CentreStatus>('ACTIVE');
  const [isUpdatingCentre, setIsUpdatingCentre] = useState<boolean>(false);
  const [centreFormError, setCentreFormError] = useState<string | null>(null);

  // Add Camera Modal state
  const [isAddCameraOpen, setIsAddCameraOpen] = useState<boolean>(false);
  const [camName, setCamName] = useState<string>('');
  const [camSourceType, setCamSourceType] = useState<CameraSourceType>('VIDEO_FILE');
  const [camSourceUrl, setCamSourceUrl] = useState<string>('');
  const [camIsActive, setCamIsActive] = useState<boolean>(true);
  const [isSubmittingCamera, setIsSubmittingCamera] = useState<boolean>(false);
  const [camFormError, setCamFormError] = useState<string | null>(null);

  // Edit Camera Modal state
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [editCamName, setEditCamName] = useState<string>('');
  const [editCamSourceType, setEditCamSourceType] = useState<CameraSourceType>('VIDEO_FILE');
  const [editCamSourceUrl, setEditCamSourceUrl] = useState<string>('');
  const [editCamIsActive, setEditCamIsActive] = useState<boolean>(true);
  const [isUpdatingCamera, setIsUpdatingCamera] = useState<boolean>(false);
  const [editCamError, setEditCamError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      if (isNaN(centreId)) {
        if (isMounted) {
          setError('Invalid Centre ID specified.');
          setIsLoading(false);
        }
        return;
      }

      try {
        const [centreData, camerasData, inventoryData, sessionsData, alertsData] = await Promise.all([
          centresApi.getCentre(centreId),
          centresApi.getCameras(centreId),
          inventoryApi.getInventory(centreId).catch(() => [] as InventoryItem[]),
          monitoringApi.listSessions({ centre_id: centreId }).catch(() => [] as MonitoringSession[]),
          alertsApi.listAlerts({ centre_id: centreId }).catch(() => [] as Alert[]),
        ]);
        if (isMounted) {
          setCentre(centreData);
          setCameras(camerasData);
          setInventory(inventoryData || []);
          setSessions(sessionsData || []);
          setAlerts(alertsData || []);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to load centre profile.';
          setError(msg);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    void fetchData();

    return () => {
      isMounted = false;
    };
  }, [centreId]);

  const reloadData = () => {
    setIsLoading(true);
    setError(null);
    Promise.all([
      centresApi.getCentre(centreId),
      centresApi.getCameras(centreId),
      inventoryApi.getInventory(centreId).catch(() => [] as InventoryItem[]),
      monitoringApi.listSessions({ centre_id: centreId }).catch(() => [] as MonitoringSession[]),
      alertsApi.listAlerts({ centre_id: centreId }).catch(() => [] as Alert[]),
    ])
      .then(([centreData, camerasData, inventoryData, sessionsData, alertsData]) => {
        setCentre(centreData);
        setCameras(camerasData);
        setInventory(inventoryData || []);
        setSessions(sessionsData || []);
        setAlerts(alertsData || []);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load centre profile.';
        setError(msg);
      })
      .finally(() => setIsLoading(false));
  };

  // Handle Edit Centre submission
  const handleOpenEditCentre = () => {
    if (!centre) return;
    setEditName(centre.name);
    setEditLocation(centre.location || '');
    setEditStatus(centre.status);
    setCentreFormError(null);
    setIsEditCentreOpen(true);
  };

  const handleUpdateCentre = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!centre) return;
    if (!editName.trim()) {
      setCentreFormError('Centre name is required.');
      return;
    }

    setIsUpdatingCentre(true);
    setCentreFormError(null);
    try {
      const updated = await centresApi.updateCentre(centre.id, {
        name: editName.trim(),
        location: editLocation.trim() || null,
        status: editStatus,
      });
      setCentre(updated);
      setIsEditCentreOpen(false);
      setSuccessMessage('Centre metadata updated successfully.');
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update centre.';
      setCentreFormError(msg);
    } finally {
      setIsUpdatingCentre(false);
    }
  };

  // Toggle Centre Status
  const handleToggleCentreStatus = async () => {
    if (!centre || !isAdmin) return;
    const nextStatus: CentreStatus = centre.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    const actionText = nextStatus === 'ACTIVE' ? 'activate' : 'deactivate';

    if (!confirm(`Are you sure you want to ${actionText} centre "${centre.name}"?`)) {
      return;
    }

    try {
      const updated = await centresApi.updateCentreStatus(centre.id, nextStatus);
      setCentre(updated);
      setSuccessMessage(`Centre status changed to ${nextStatus}.`);
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to change status.';
      alert(msg);
    }
  };

  // Handle Add Camera
  const handleOpenAddCamera = () => {
    setCamName('');
    setCamSourceType('VIDEO_FILE');
    setCamSourceUrl('');
    setCamIsActive(true);
    setCamFormError(null);
    setIsAddCameraOpen(true);
  };

  const handleCreateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!camName.trim()) {
      setCamFormError('Camera feed name is required.');
      return;
    }
    if (!camSourceUrl.trim()) {
      setCamFormError('Source path or camera stream URL is required.');
      return;
    }

    setIsSubmittingCamera(true);
    setCamFormError(null);
    try {
      const created = await centresApi.createCamera(centreId, {
        name: camName.trim(),
        source_type: camSourceType,
        source_url: camSourceUrl.trim(),
        is_active: camIsActive,
      });
      setCameras((prev) => [...prev, created]);
      if (centre) {
        setCentre({ ...centre, camera_count: centre.camera_count + 1 });
      }
      setIsAddCameraOpen(false);
      setSuccessMessage(`Camera "${created.name}" configured successfully.`);
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add camera feed.';
      setCamFormError(msg);
    } finally {
      setIsSubmittingCamera(false);
    }
  };

  // Handle Edit Camera
  const handleOpenEditCamera = (camera: Camera) => {
    setEditingCamera(camera);
    setEditCamName(camera.name);
    setEditCamSourceType(camera.source_type);
    setEditCamSourceUrl(camera.source_url);
    setEditCamIsActive(camera.is_active);
    setEditCamError(null);
  };

  const handleUpdateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCamera) return;
    if (!editCamName.trim()) {
      setEditCamError('Camera feed name is required.');
      return;
    }
    if (!editCamSourceUrl.trim()) {
      setEditCamError('Source URL or path is required.');
      return;
    }

    setIsUpdatingCamera(true);
    setEditCamError(null);
    try {
      const updated = await centresApi.updateCamera(centreId, editingCamera.id, {
        name: editCamName.trim(),
        source_type: editCamSourceType,
        source_url: editCamSourceUrl.trim(),
        is_active: editCamIsActive,
      });
      setCameras((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setEditingCamera(null);
      setSuccessMessage(`Camera "${updated.name}" updated successfully.`);
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update camera.';
      setEditCamError(msg);
    } finally {
      setIsUpdatingCamera(false);
    }
  };

  // Handle Toggle Camera Status
  const handleToggleCameraStatus = async (camera: Camera) => {
    if (!isAdmin) return;
    const nextStatus = !camera.is_active;

    try {
      const updated = await centresApi.updateCameraStatus(centreId, camera.id, nextStatus);
      setCameras((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setSuccessMessage(`Camera "${camera.name}" is now ${nextStatus ? 'ACTIVE' : 'INACTIVE'}.`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to toggle camera status.';
      alert(msg);
    }
  };

  if (isLoading) {
    return (
      <div className="py-12">
        <LoadingState message="Loading centre profile and camera configurations..." />
      </div>
    );
  }

  if (error || !centre) {
    return (
      <div className="space-y-4">
        <Link href="/centres">
          <Button variant="outline" size="sm" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Centres</span>
          </Button>
        </Link>
        <Card>
          <CardContent className="p-8">
            <ErrorState
              title="Centre Not Found"
              message={error || 'Unable to find training centre.'}
              onRetry={reloadData}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  const activeCamerasCount = cameras.filter((c) => c.is_active).length;

  return (
    <div className="space-y-6">
      {/* Top Navigation & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/centres">
            <Button variant="outline" size="sm" className="p-2 border-slate-700 hover:border-slate-600">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-white">{centre.name}</h1>
              <Badge variant="outline" className="font-mono text-xs text-slate-300 border-slate-700">
                {centre.centre_code}
              </Badge>
              <Badge variant={centre.status === 'ACTIVE' ? 'success' : 'danger'}>
                {centre.status}
              </Badge>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {centre.location || 'Location details not specified'} • Registered on {new Date(centre.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Admin Quick Actions */}
        {isAdmin && (
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenEditCentre}
              className="text-xs gap-1.5 border-slate-700 hover:border-slate-600"
            >
              <Edit2 className="w-3.5 h-3.5 text-slate-400" />
              <span>Edit Details</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleCentreStatus}
              className={`text-xs gap-1.5 ${
                centre.status === 'ACTIVE'
                  ? 'text-rose-400 border-rose-500/30 hover:bg-rose-500/10'
                  : 'text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10'
              }`}
            >
              {centre.status === 'ACTIVE' ? (
                <>
                  <PowerOff className="w-3.5 h-3.5" />
                  <span>Deactivate Centre</span>
                </>
              ) : (
                <>
                  <Power className="w-3.5 h-3.5" />
                  <span>Activate Centre</span>
                </>
              )}
            </Button>
          </div>
        )}
      </div>

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

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Monitoring Readiness</div>
          <div className="my-2">
            <Badge variant={centre.status === 'ACTIVE' && activeCamerasCount > 0 ? 'success' : 'warning'}>
              {centre.status === 'ACTIVE' && activeCamerasCount > 0
                ? 'Ready for Capture'
                : centre.status !== 'ACTIVE'
                ? 'Centre Inactive'
                : 'Awaiting Feeds'}
            </Badge>
          </div>
          <p className="text-[11px] text-slate-500">
            {activeCamerasCount > 0 ? `${activeCamerasCount} active stream(s) online` : 'No active camera feeds'}
          </p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Configured Feeds</div>
          <div className="my-2 text-2xl font-bold text-white">{cameras.length}</div>
          <p className="text-[11px] text-slate-500">{activeCamerasCount} active / {cameras.length - activeCamerasCount} inactive</p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Sanctioned Assets</div>
          <div className="my-2 text-2xl font-bold text-slate-500">--</div>
          <p className="text-[11px] text-slate-500">Module 6: Excel upload</p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Active Alerts</div>
          <div className="my-2 text-2xl font-bold text-slate-500">--</div>
          <p className="text-[11px] text-slate-500">Module 9: Discrepancy checks</p>
        </Card>
      </div>

      {/* Main Grid: Cameras & Future Staged Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Cameras */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <CameraIcon className="w-4 h-4 text-emerald-400" />
                <span>Installed Cameras & Video Feeds</span>
              </CardTitle>
              {isAdmin && (
                <Button
                  size="sm"
                  onClick={handleOpenAddCamera}
                  className="text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Camera</span>
                </Button>
              )}
            </CardHeader>
            <CardContent className="p-0">
              {cameras.length > 0 ? (
                <div className="divide-y divide-slate-800">
                  {cameras.map((camera) => (
                    <div
                      key={camera.id}
                      className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/40 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-sm">{camera.name}</span>
                          <Badge
                            variant={camera.source_type === 'VIDEO_FILE' ? 'outline' : 'default'}
                            className="text-[10px] uppercase font-mono"
                          >
                            {camera.source_type === 'VIDEO_FILE' ? 'Video File (MP4)' : 'RTSP / Camera'}
                          </Badge>
                          <Badge variant={camera.is_active ? 'success' : 'danger'} className="text-[10px]">
                            {camera.is_active ? 'ACTIVE' : 'INACTIVE'}
                          </Badge>
                        </div>
                        <p className="text-xs font-mono text-slate-400 break-all">
                          {camera.source_url}
                        </p>
                      </div>

                      {isAdmin && (
                        <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleCameraStatus(camera)}
                            title={camera.is_active ? 'Deactivate camera' : 'Activate camera'}
                            className={`text-xs gap-1 ${
                              camera.is_active
                                ? 'text-slate-400 hover:text-rose-400 hover:bg-rose-500/10'
                                : 'text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10'
                            }`}
                          >
                            {camera.is_active ? (
                              <>
                                <PowerOff className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline">Disable</span>
                              </>
                            ) : (
                              <>
                                <Power className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline">Enable</span>
                              </>
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenEditCamera(camera)}
                            className="text-xs gap-1 border-slate-700 hover:border-slate-600"
                          >
                            <Edit2 className="w-3 h-3 text-slate-400" />
                            <span>Edit</span>
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={CameraIcon}
                  title="No Camera Feeds Configured"
                  description="Register camera feed sources (pre-recorded benchmark MP4 files or camera streams) to begin monitoring this facility."
                  className="p-8"
                  action={
                    isAdmin ? (
                      <Button
                        size="sm"
                        onClick={handleOpenAddCamera}
                        className="text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add First Camera</span>
                      </Button>
                    ) : undefined
                  }
                />
              )}
            </CardContent>
          </Card>

          {/* Active Section: Monitoring History */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm text-slate-300">
                  <Clock className="w-4 h-4 text-emerald-400" />
                  <span>Monitoring History</span>
                </CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Recent inspection sessions executed for this centre
                </p>
              </div>
              <Link href="/monitoring">
                <Button variant="outline" size="sm" className="text-xs">
                  <span>Start Session</span>
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              {sessions.length > 0 ? (
                <div className="divide-y divide-slate-800 text-xs">
                  {sessions.slice(0, 5).map((s) => (
                    <div key={s.id} className="p-3.5 flex items-center justify-between hover:bg-slate-800/30">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">Session #{s.id}</span>
                          <Badge
                            variant={
                              s.status === 'COMPLETED'
                                ? 'success'
                                : s.status === 'RUNNING'
                                ? 'default'
                                : 'outline'
                            }
                            className="text-[10px]"
                          >
                            {s.status}
                          </Badge>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Date: {s.session_date} • Headcount: {s.physical_attendance}
                        </p>
                      </div>
                      <Link href={`/monitoring`}>
                        <Button variant="ghost" size="sm" className="text-xs h-7">
                          View
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-xs text-slate-500">
                  No monitoring sessions conducted for this centre yet.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Live Surveillance & Compliance Modules */}
        <div className="space-y-6">
          {/* Latest Monitoring Session & Compliance Overview */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm text-slate-300">
                <Activity className="w-4 h-4 text-blue-400" />
                <span>Latest Monitoring Run</span>
              </CardTitle>
              {sessions.length > 0 && (
                <Badge variant="outline" className="text-[10px] font-mono">
                  Session #{sessions[0].id}
                </Badge>
              )}
            </CardHeader>
            <CardContent className="p-4 text-xs space-y-3">
              {sessions.length > 0 ? (
                <div className="space-y-2.5">
                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">Execution Status</span>
                    <Badge
                      variant={
                        sessions[0].status === 'COMPLETED'
                          ? 'success'
                          : sessions[0].status === 'RUNNING'
                          ? 'default'
                          : 'outline'
                      }
                    >
                      {sessions[0].status}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">Recorded Headcount</span>
                    <span className="font-mono text-slate-200">
                      {sessions[0].physical_attendance}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">Snapshot Count</span>
                    <span className="font-mono text-slate-200">
                      {sessions[0].snapshots?.length ?? 0} frames
                    </span>
                  </div>
                  <div className="pt-2 flex justify-end">
                    <Link href={`/monitoring`}>
                      <Button variant="outline" size="sm" className="text-xs w-full">
                        Open Monitoring Workbench →
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 text-center py-3">
                  No monitoring sessions have been initialized for this centre.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Compliance Alerts Card */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm text-slate-300">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>Compliance Alerts</span>
                </CardTitle>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Evidence-backed discrepancy flags
                </p>
              </div>
              <Badge variant="outline" className="text-[10px] font-mono">
                {alerts.length} Total
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              {alerts.length > 0 ? (
                <div className="divide-y divide-slate-800 text-xs">
                  {alerts.slice(0, 4).map((a) => (
                    <Link
                      key={a.id}
                      href={`/alerts/${a.id}`}
                      className="p-3 block hover:bg-slate-800/40 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-200 truncate">
                          {a.title}
                        </span>
                        <Badge
                          variant={
                            a.status === 'VERIFIED'
                              ? 'danger'
                              : a.status === 'FALSE_POSITIVE'
                              ? 'success'
                              : 'warning'
                          }
                          className="text-[10px]"
                        >
                          {a.status}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Diff: {a.difference} • {a.severity} Severity
                      </p>
                    </Link>
                  ))}
                  <div className="p-2.5 text-center">
                    <Link
                      href={`/alerts?centre_id=${centreId}`}
                      className="text-xs text-emerald-400 hover:underline"
                    >
                      View all alerts for this centre →
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-slate-500">
                  No discrepancy alerts flagged for this centre.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sanctioned Inventory Baseline Card */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm text-slate-300">
                  <FileSpreadsheet className="w-4 h-4 text-purple-400" />
                  <span>Sanctioned Inventory Baseline</span>
                </CardTitle>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Mandated physical assets for infrastructure comparison
                </p>
              </div>
              <Link href="/inventory">
                <Button variant="outline" size="sm" className="text-xs">
                  Upload Excel
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              {inventory.length > 0 ? (
                <div className="divide-y divide-slate-800 text-xs">
                  {inventory.slice(0, 5).map((item) => (
                    <div key={item.id} className="p-3 flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-200">{item.item_name}</p>
                        <p className="text-[10px] text-slate-500">
                          Category: {item.category || 'Standard Equipment'}
                        </p>
                      </div>
                      <span className="font-mono text-emerald-400 font-semibold">
                        {item.expected_quantity} units
                      </span>
                    </div>
                  ))}
                  {inventory.length > 5 && (
                    <div className="p-2 text-center text-[11px] text-slate-400">
                      + {inventory.length - 5} more items in baseline
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-slate-500">
                  No sanctioned inventory baseline imported yet.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Centre Modal */}
      <Modal
        isOpen={isEditCentreOpen}
        onClose={() => !isUpdatingCentre && setIsEditCentreOpen(false)}
        title="Edit Centre Details"
        description={`Update information for ${centre.centre_code}`}
      >
        <form onSubmit={handleUpdateCentre} className="space-y-4 pt-2">
          {centreFormError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{centreFormError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Centre Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              disabled={isUpdatingCentre}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Location / Address
            </label>
            <input
              type="text"
              value={editLocation}
              onChange={(e) => setEditLocation(e.target.value)}
              disabled={isUpdatingCentre}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Operational Status
            </label>
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as CentreStatus)}
              disabled={isUpdatingCentre}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
              <option value="SUSPENDED">SUSPENDED</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsEditCentreOpen(false)}
              disabled={isUpdatingCentre}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isUpdatingCentre}
              className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[100px]"
            >
              {isUpdatingCentre ? (
                <span className="flex items-center gap-1.5">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </span>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Camera Modal */}
      <Modal
        isOpen={isAddCameraOpen}
        onClose={() => !isSubmittingCamera && setIsAddCameraOpen(false)}
        title="Register New Camera Feed"
        description={`Add a video feed source to ${centre.name}`}
      >
        <form onSubmit={handleCreateCamera} className="space-y-4 pt-2">
          {camFormError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{camFormError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Feed / Camera Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={camName}
              onChange={(e) => setCamName(e.target.value)}
              placeholder="e.g. Computer Lab Front Camera"
              disabled={isSubmittingCamera}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Source Type <span className="text-rose-400">*</span>
            </label>
            <select
              value={camSourceType}
              onChange={(e) => setCamSourceType(e.target.value as CameraSourceType)}
              disabled={isSubmittingCamera}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="VIDEO_FILE">VIDEO_FILE — Pre-recorded MP4 test file</option>
              <option value="CAMERA">CAMERA — Live stream / RTSP feed URL</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Source Path / URL <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={camSourceUrl}
              onChange={(e) => setCamSourceUrl(e.target.value)}
              placeholder={
                camSourceType === 'VIDEO_FILE'
                  ? 'e.g. data/videos/classroom_test.mp4'
                  : 'e.g. rtsp://192.168.1.50:554/stream1'
              }
              disabled={isSubmittingCamera}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 text-xs"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              {camSourceType === 'VIDEO_FILE'
                ? 'Relative path to video file on the server file system.'
                : 'Direct stream URI for RTSP/IP camera device.'}
            </p>
          </div>

          <div>
            <label className="flex items-center gap-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={camIsActive}
                onChange={(e) => setCamIsActive(e.target.checked)}
                disabled={isSubmittingCamera}
                className="rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0"
              />
              <span className="text-xs text-slate-300 font-medium">Activate camera feed immediately</span>
            </label>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddCameraOpen(false)}
              disabled={isSubmittingCamera}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmittingCamera}
              className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[110px]"
            >
              {isSubmittingCamera ? (
                <span className="flex items-center gap-1.5">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Adding...</span>
                </span>
              ) : (
                'Add Camera'
              )}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit Camera Modal */}
      {editingCamera && (
        <Modal
          isOpen={true}
          onClose={() => !isUpdatingCamera && setEditingCamera(null)}
          title="Edit Camera Feed"
          description={`Update configuration for ${editingCamera.name}`}
        >
          <form onSubmit={handleUpdateCamera} className="space-y-4 pt-2">
            {editCamError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{editCamError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Feed / Camera Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                value={editCamName}
                onChange={(e) => setEditCamName(e.target.value)}
                disabled={isUpdatingCamera}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Source Type <span className="text-rose-400">*</span>
              </label>
              <select
                value={editCamSourceType}
                onChange={(e) => setEditCamSourceType(e.target.value as CameraSourceType)}
                disabled={isUpdatingCamera}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              >
                <option value="VIDEO_FILE">VIDEO_FILE — Pre-recorded MP4 test file</option>
                <option value="CAMERA">CAMERA — Live stream / RTSP feed URL</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Source Path / URL <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                value={editCamSourceUrl}
                onChange={(e) => setEditCamSourceUrl(e.target.value)}
                disabled={isUpdatingCamera}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 text-xs"
              />
            </div>

            <div>
              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={editCamIsActive}
                  onChange={(e) => setEditCamIsActive(e.target.checked)}
                  disabled={isUpdatingCamera}
                  className="rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0"
                />
                <span className="text-xs text-slate-300 font-medium">Camera feed active</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setEditingCamera(null)}
                disabled={isUpdatingCamera}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isUpdatingCamera}
                className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[110px]"
              >
                {isUpdatingCamera ? (
                  <span className="flex items-center gap-1.5">
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </span>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
