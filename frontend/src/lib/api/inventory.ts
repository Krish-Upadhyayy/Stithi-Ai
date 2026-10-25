import { fetchApi } from './client';
import {
  InventoryItem,
  InventoryItemCreateInput,
  InventoryItemUpdateInput,
  InventoryUploadPreviewResponse,
  InventoryConfirmRequest,
  InventoryConfirmResponse,
} from '../types/inventory';

export const inventoryApi = {
  async getInventory(centreId: number): Promise<InventoryItem[]> {
    return fetchApi<InventoryItem[]>(`centres/${centreId}/inventory`, { cache: 'no-store' });
  },

  async listInventory(centreId?: number): Promise<InventoryItem[]> {
    if (centreId) {
      return this.getInventory(centreId);
    }
    return fetchApi<InventoryItem[]>('inventory', { cache: 'no-store' });
  },

  async uploadInventoryExcel(centreId: number, file: File): Promise<InventoryUploadPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return fetchApi<InventoryUploadPreviewResponse>(`centres/${centreId}/inventory/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  async confirmInventoryImport(
    centreId: number,
    data: InventoryConfirmRequest
  ): Promise<InventoryConfirmResponse> {
    return fetchApi<InventoryConfirmResponse>(`centres/${centreId}/inventory/confirm`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createInventoryItem(
    centreId: number,
    data: InventoryItemCreateInput
  ): Promise<InventoryItem> {
    return fetchApi<InventoryItem>(`centres/${centreId}/inventory`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateInventoryItem(
    centreId: number,
    itemId: number,
    data: InventoryItemUpdateInput
  ): Promise<InventoryItem> {
    return fetchApi<InventoryItem>(`centres/${centreId}/inventory/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteInventoryItem(
    centreId: number,
    itemId: number
  ): Promise<{ message: string; id: number; centre_id: number }> {
    return fetchApi<{ message: string; id: number; centre_id: number }>(
      `centres/${centreId}/inventory/${itemId}`,
      {
        method: 'DELETE',
      }
    );
  },
};
