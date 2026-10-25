'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileSpreadsheet,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Plus,
  Edit2,
  Trash2,
  RotateCw,
  Search,
  ArrowRight,
  Info,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingState } from '@/components/ui/LoadingState';
import { Modal } from '@/components/ui/Modal';
import { centresApi } from '@/lib/api/centres';
import { inventoryApi } from '@/lib/api/inventory';
import { Centre } from '@/lib/types/centre';
import {
  InventoryItem,
  InventoryUploadPreviewResponse,
} from '@/lib/types/inventory';
import { useAuth } from '@/lib/auth/auth-context';

export default function InventoryPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  // Centre selection
  const [centres, setCentres] = useState<Centre[]>([]);
  const [selectedCentreId, setSelectedCentreId] = useState<number | null>(null);
  const [isCentresLoading, setIsCentresLoading] = useState<boolean>(true);

  // Inventory list state
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [isInventoryLoading, setIsInventoryLoading] = useState<boolean>(false);
  const [inventoryError, setInventoryError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadState, setUploadState] = useState<
    'idle' | 'uploading' | 'preview' | 'importing'
  >('idle');
  const [previewData, setPreviewData] = useState<InventoryUploadPreviewResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [replaceExisting, setReplaceExisting] = useState<boolean>(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Manual Add Item modal
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [addName, setAddName] = useState<string>('');
  const [addCategory, setAddCategory] = useState<string>('');
  const [addQuantity, setAddQuantity] = useState<number>(1);
  const [isAdding, setIsAdding] = useState<boolean>(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Manual Edit Item modal
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [editName, setEditName] = useState<string>('');
  const [editCategory, setEditCategory] = useState<string>('');
  const [editQuantity, setEditQuantity] = useState<number>(0);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Initial load: fetch centres
  useEffect(() => {
    let isMounted = true;
    centresApi
      .getCentres()
      .then((data) => {
        if (!isMounted) return;
        setCentres(data);
        if (data.length > 0) {
          setSelectedCentreId(data[0].id);
        }
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : 'Failed to retrieve centres.';
        setNotification({ type: 'error', message: msg });
      })
      .finally(() => {
        if (isMounted) setIsCentresLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedCentreId) return;

    let isMounted = true;

    async function loadData() {
      try {
        const items = await inventoryApi.getInventory(selectedCentreId!);
        if (isMounted) setInventory(items);
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to load inventory for centre.';
          setInventoryError(msg);
        }
      } finally {
        if (isMounted) setIsInventoryLoading(false);
      }
    }

    void loadData();

    return () => {
      isMounted = false;
    };
  }, [selectedCentreId]);

  const reloadInventory = useCallback((centreId: number) => {
    setIsInventoryLoading(true);
    setInventoryError(null);
    inventoryApi
      .getInventory(centreId)
      .then((items) => setInventory(items))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to load inventory for centre.';
        setInventoryError(msg);
      })
      .finally(() => setIsInventoryLoading(false));
  }, []);

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  // --- EXCEL UPLOAD HANDLERS ---
  const handleOpenUploadModal = () => {
    setPreviewData(null);
    setUploadError(null);
    setUploadState('idle');
    setReplaceExisting(true);
    setIsUploadModalOpen(true);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      setUploadError('Only .xlsx spreadsheet files are accepted.');
      return;
    }

    if (!selectedCentreId) {
      setUploadError('Please select a target training centre first.');
      return;
    }

    setUploadError(null);
    setUploadState('uploading');

    try {
      const preview = await inventoryApi.uploadInventoryExcel(selectedCentreId, file);
      setPreviewData(preview);
      setUploadState('preview');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to upload and validate spreadsheet.';
      setUploadError(msg);
      setUploadState('idle');
    }
  };

  const handleConfirmImport = async () => {
    if (!selectedCentreId || !previewData || !previewData.is_valid) return;

    setUploadState('importing');
    setUploadError(null);

    try {
      const res = await inventoryApi.confirmInventoryImport(selectedCentreId, {
        items: previewData.items.map((i) => ({
          item_name: i.item_name,
          category: i.category,
          expected_quantity: i.expected_quantity,
        })),
        replace_existing: replaceExisting,
      });

      showNotification('success', res.message);
      setIsUploadModalOpen(false);
      reloadInventory(selectedCentreId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Database import failed.';
      setUploadError(msg);
      setUploadState('preview');
    }
  };

  // --- MANUAL ITEM HANDLERS ---
  const handleOpenAddModal = () => {
    setAddName('');
    setAddCategory('');
    setAddQuantity(1);
    setAddError(null);
    setIsAddModalOpen(true);
  };

  const handleCreateManualItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCentreId) return;

    const trimmedName = addName.trim();
    if (!trimmedName) {
      setAddError('Asset item name is required.');
      return;
    }
    if (addQuantity < 0) {
      setAddError('Expected quantity must be 0 or greater.');
      return;
    }

    setIsAdding(true);
    setAddError(null);
    try {
      const created = await inventoryApi.createInventoryItem(selectedCentreId, {
        item_name: trimmedName,
        category: addCategory.trim() || null,
        expected_quantity: Number(addQuantity),
      });

      setInventory((prev) => [...prev, created]);
      setIsAddModalOpen(false);
      showNotification('success', `Added "${created.item_name}" to sanctioned inventory.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create inventory item.';
      setAddError(msg);
    } finally {
      setIsAdding(false);
    }
  };

  const handleOpenEditModal = (item: InventoryItem) => {
    setEditingItem(item);
    setEditName(item.item_name);
    setEditCategory(item.category || '');
    setEditQuantity(item.expected_quantity);
    setEditError(null);
  };

  const handleUpdateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCentreId || !editingItem) return;

    const trimmedName = editName.trim();
    if (!trimmedName) {
      setEditError('Asset item name is required.');
      return;
    }
    if (editQuantity < 0) {
      setEditError('Expected quantity must be 0 or greater.');
      return;
    }

    setIsUpdating(true);
    setEditError(null);
    try {
      const updated = await inventoryApi.updateInventoryItem(selectedCentreId, editingItem.id, {
        item_name: trimmedName,
        category: editCategory.trim() || null,
        expected_quantity: Number(editQuantity),
      });

      setInventory((prev) => prev.map((it) => (it.id === updated.id ? updated : it)));
      setEditingItem(null);
      showNotification('success', `Updated "${updated.item_name}".`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update item.';
      setEditError(msg);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteItem = async (item: InventoryItem) => {
    if (!selectedCentreId || !isAdmin) return;
    if (!confirm(`Are you sure you want to remove "${item.item_name}" from the sanctioned inventory?`)) {
      return;
    }

    try {
      await inventoryApi.deleteInventoryItem(selectedCentreId, item.id);
      setInventory((prev) => prev.filter((it) => it.id !== item.id));
      showNotification('success', `Removed "${item.item_name}".`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete item.';
      alert(msg);
    }
  };

  const selectedCentre = centres.find((c) => c.id === selectedCentreId);
  const totalSanctionedQuantity = inventory.reduce((acc, curr) => acc + curr.expected_quantity, 0);

  const filteredInventory = inventory.filter(
    (item) =>
      item.item_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.category && item.category.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sanctioned Infrastructure Baseline"
        description="Upload and manage sanctioned government equipment allocations. Visual detections from camera feeds will be compared against these expected quantities during compliance audits."
        action={
          isAdmin && selectedCentreId ? (
            <div className="flex items-center gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenAddModal}
                className="gap-1.5 text-xs border-slate-700 hover:border-slate-600"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Item Manually</span>
              </Button>
              <Button
                size="sm"
                onClick={handleOpenUploadModal}
                className="gap-2 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <UploadCloud className="w-4 h-4" />
                <span>Upload Excel (.xlsx)</span>
              </Button>
            </div>
          ) : undefined
        }
      />

      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-3.5 rounded-lg border text-xs flex items-center justify-between animate-in fade-in ${
            notification.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="hover:opacity-75">
            ×
          </button>
        </div>
      )}

      {/* Centre Selector & Baseline Stats Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Selector Card */}
        <Card className="md:col-span-2 p-4 bg-slate-900 border-slate-800 flex flex-col justify-between">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Select Training Centre
            </label>
            {isCentresLoading ? (
              <div className="text-xs text-slate-500">Loading centres...</div>
            ) : centres.length > 0 ? (
              <select
                value={selectedCentreId || ''}
                onChange={(e) => setSelectedCentreId(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              >
                {centres.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.centre_code}) • {c.location || 'Location Unspecified'}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-slate-500">No training centres registered. Create one in Centres first.</p>
            )}
          </div>
          {selectedCentre && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800 text-xs text-slate-400">
              <span className="font-medium text-slate-300">{selectedCentre.name}</span>
              <Badge variant="outline" className="font-mono text-[10px]">
                {selectedCentre.centre_code}
              </Badge>
              <Badge variant={selectedCentre.status === 'ACTIVE' ? 'success' : 'danger'} className="text-[10px]">
                {selectedCentre.status}
              </Badge>
            </div>
          )}
        </Card>

        {/* Unique Asset Types Stat */}
        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Sanctioned Asset Types</div>
          <div className="my-2 text-2xl font-bold text-white">{inventory.length}</div>
          <p className="text-[11px] text-slate-500">Distinct inventory classifications</p>
        </Card>

        {/* Total Expected Quantity Stat */}
        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Total Sanctioned Units</div>
          <div className="my-2 text-2xl font-bold text-emerald-400">{totalSanctionedQuantity}</div>
          <p className="text-[11px] text-slate-500">Expected physical items on-premise</p>
        </Card>
      </div>

      {/* Compliance Engine Notice Banner */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-3">
        <Info className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 space-y-1">
          <p className="font-semibold text-slate-200">
            How this inventory interacts with the Compliance Engine:
          </p>
          <p>
            The quantities defined below represent the sanctioned baseline (<span className="text-emerald-300 font-mono">Expected Quantity</span>). During monitoring sessions, the Stithi AI infrastructure pipeline observes visible equipment on snapshots (<span className="text-cyan-300 font-mono">AI Observed Quantity</span>). The compliance engine identifies potential infrastructure discrepancies.
          </p>
          <p className="text-slate-400 text-[11px]">
            Infrastructure observations are based on visual detection and do not establish mechanical or electrical functionality.
          </p>
        </div>
      </div>

      {/* Search Bar & Inventory Table */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3">
          <div className="space-y-0.5">
            <CardTitle className="text-base flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-purple-400" />
              <span>Current Sanctioned Inventory Baseline</span>
            </CardTitle>
            <p className="text-xs text-slate-400">
              Items currently registered for {selectedCentre?.name || 'selected centre'}
            </p>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-72">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter items or category..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isInventoryLoading ? (
            <div className="p-12">
              <LoadingState message="Fetching sanctioned inventory records..." />
            </div>
          ) : inventoryError ? (
            <div className="p-8">
              <ErrorState
                title="Failed to Load Inventory"
                message={inventoryError}
                onRetry={() => selectedCentreId && reloadInventory(selectedCentreId)}
              />
            </div>
          ) : filteredInventory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 border-y border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Item Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-center">Sanctioned Expected Quantity</th>
                    <th className="py-3 px-4">Last Updated</th>
                    {isAdmin && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredInventory.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-white">{item.item_name}</td>
                      <td className="py-3.5 px-4">
                        {item.category ? (
                          <Badge variant="outline" className="text-[10px] text-slate-300 border-slate-700">
                            {item.category}
                          </Badge>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="inline-block px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 font-bold text-emerald-400 font-mono text-sm">
                          {item.expected_quantity}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                        {new Date(item.updated_at).toLocaleString()}
                      </td>
                      {isAdmin && (
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenEditModal(item)}
                              className="text-xs p-1.5 h-auto text-slate-400 hover:text-white"
                              title="Edit item"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteItem(item)}
                              className="text-xs p-1.5 h-auto text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                              title="Delete item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8">
              <EmptyState
                icon={FileSpreadsheet}
                title="No Sanctioned Inventory Baseline"
                description={`Upload an approved .xlsx spreadsheet or add items manually to specify expected equipment for ${
                  selectedCentre?.name || 'this facility'
                }.`}
                action={
                  isAdmin && selectedCentreId ? (
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleOpenAddModal}
                        className="text-xs"
                      >
                        Add Item Manually
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleOpenUploadModal}
                        className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        Upload Excel Spreadsheet
                      </Button>
                    </div>
                  ) : undefined
                }
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* --- EXCEL UPLOAD & PREVIEW MODAL --- */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => uploadState !== 'importing' && setIsUploadModalOpen(false)}
        title="Upload Sanctioned Equipment Spreadsheet"
        description={`Import infrastructure allocation for ${selectedCentre?.name || 'selected centre'}`}
        className="max-w-2xl"
      >
        <div className="space-y-4 pt-2">
          {/* Format Specification Hint */}
          <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/80 text-xs text-slate-300 space-y-1">
            <p className="font-semibold text-slate-200">Required Excel Format (.xlsx):</p>
            <p className="text-slate-400">
              Columns: <span className="font-mono text-emerald-300 font-medium">Item Name</span>,{' '}
              <span className="font-mono text-emerald-300 font-medium">Expected Quantity</span> (non-negative integer),{' '}
              <span className="font-mono text-slate-400">Category</span> (optional).
            </p>
          </div>

          {/* Upload Dropzone */}
          {uploadState === 'idle' && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-700 hover:border-emerald-500/60 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-950/40 space-y-3"
            >
              <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-emerald-400">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-200">Click to choose or drag .xlsx file here</p>
                <p className="text-xs text-slate-500 mt-1">Accepts standard OpenXML .xlsx files up to 10MB</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          )}

          {/* Loading / Validating State */}
          {uploadState === 'uploading' && (
            <div className="p-8 text-center space-y-3">
              <RotateCw className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
              <p className="text-sm text-slate-200 font-medium">Parsing and validating spreadsheet rows...</p>
              <p className="text-xs text-slate-500">Checking column headers, non-negative quantities, and duplicate keys</p>
            </div>
          )}

          {/* Upload Errors */}
          {uploadError && (
            <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Preview State: Validated or Error Table */}
          {uploadState === 'preview' && previewData && (
            <div className="space-y-4">
              {/* Validation Status Card */}
              {previewData.is_valid ? (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>
                      Spreadsheet validated successfully ({previewData.valid_rows_count} valid items parsed, 0 errors).
                    </span>
                  </div>
                  <Badge variant="success" className="text-[10px]">
                    Ready to Import
                  </Badge>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>
                      Validation failed: Found {previewData.error_count} issue(s) in {previewData.filename}.
                    </span>
                  </div>
                  <div className="max-h-36 overflow-y-auto space-y-1 pl-6">
                    {previewData.errors.map((err, idx) => (
                      <p key={idx} className="text-[11px] text-rose-200">
                        • {err.message}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Preview Table */}
              <div className="border border-slate-800 rounded-lg overflow-hidden max-h-56 overflow-y-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-800/80 sticky top-0 text-[11px] uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="py-2 px-3">Row</th>
                      <th className="py-2 px-3">Item Name</th>
                      <th className="py-2 px-3">Category</th>
                      <th className="py-2 px-3 text-right">Expected Qty</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {previewData.items.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="py-2 px-3 font-mono text-slate-500">{item.row}</td>
                        <td className="py-2 px-3 font-semibold text-white">{item.item_name}</td>
                        <td className="py-2 px-3 text-slate-400">{item.category || '—'}</td>
                        <td className="py-2 px-3 text-right font-mono text-emerald-400 font-bold">
                          {item.expected_quantity}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Replace Option Checkbox */}
              {previewData.is_valid && (
                <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/60">
                  <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={replaceExisting}
                      onChange={(e) => setReplaceExisting(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0"
                    />
                    <div>
                      <span className="font-semibold text-white">Replace current inventory</span>
                      <p className="text-[11px] text-slate-500">
                        Replaces the current baseline for this centre to avoid stale duplicate entries.
                      </p>
                    </div>
                  </label>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setUploadState('idle');
                    setPreviewData(null);
                  }}
                  className="text-xs"
                >
                  Choose Different File
                </Button>

                {previewData.is_valid && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleConfirmImport}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs gap-1.5"
                  >
                    <span>Confirm & Save Sanctioned Inventory</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Importing State */}
          {uploadState === 'importing' && (
            <div className="p-8 text-center space-y-3">
              <RotateCw className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
              <p className="text-sm text-slate-200 font-medium">Persisting sanctioned equipment to MySQL...</p>
              <p className="text-xs text-slate-500">Executing atomic transaction</p>
            </div>
          )}
        </div>
      </Modal>

      {/* --- MANUAL ADD ITEM MODAL --- */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => !isAdding && setIsAddModalOpen(false)}
        title="Add Sanctioned Asset Manually"
        description={`Record equipment directly for ${selectedCentre?.name || 'selected centre'}`}
      >
        <form onSubmit={handleCreateManualItem} className="space-y-4 pt-2">
          {addError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{addError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Item Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              placeholder="e.g. Computer, Sewing Machine, Projector"
              disabled={isAdding}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Category</label>
            <input
              type="text"
              value={addCategory}
              onChange={(e) => setAddCategory(e.target.value)}
              placeholder="e.g. IT Equipment, Workshop, Furniture"
              disabled={isAdding}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Expected Sanctioned Quantity <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              min="0"
              value={addQuantity}
              onChange={(e) => setAddQuantity(Math.max(0, parseInt(e.target.value, 10) || 0))}
              disabled={isAdding}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddModalOpen(false)}
              disabled={isAdding}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isAdding}
              className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[100px]"
            >
              {isAdding ? (
                <span className="flex items-center gap-1.5">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </span>
              ) : (
                'Add Item'
              )}
            </Button>
          </div>
        </form>
      </Modal>

      {/* --- MANUAL EDIT ITEM MODAL --- */}
      {editingItem && (
        <Modal
          isOpen={true}
          onClose={() => !isUpdating && setEditingItem(null)}
          title="Edit Sanctioned Equipment"
          description={`Update details for ${editingItem.item_name}`}
        >
          <form onSubmit={handleUpdateItem} className="space-y-4 pt-2">
            {editError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{editError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Item Name <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                disabled={isUpdating}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Category</label>
              <input
                type="text"
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                disabled={isUpdating}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Expected Sanctioned Quantity <span className="text-rose-400">*</span>
              </label>
              <input
                type="number"
                min="0"
                value={editQuantity}
                onChange={(e) => setEditQuantity(Math.max(0, parseInt(e.target.value, 10) || 0))}
                disabled={isUpdating}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setEditingItem(null)}
                disabled={isUpdating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isUpdating}
                className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[100px]"
              >
                {isUpdating ? (
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
