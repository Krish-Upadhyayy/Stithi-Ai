import { fetchApi } from './client';
import {
  Centre,
  CentreStatus,
  CentreCreateInput,
  CentreUpdateInput,
  Camera,
  CameraCreateInput,
  CameraUpdateInput,
} from '../types/centre';

export const centresApi = {
  // Centre operations
  async getCentres(): Promise<Centre[]> {
    return fetchApi<Centre[]>('centres', { cache: 'no-store' });
  },

  async listCentres(): Promise<Centre[]> {
    return this.getCentres();
  },

  async getCentre(id: number): Promise<Centre> {
    return fetchApi<Centre>(`centres/${id}`, { cache: 'no-store' });
  },

  async createCentre(data: CentreCreateInput): Promise<Centre> {
    return fetchApi<Centre>('centres', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateCentre(id: number, data: CentreUpdateInput): Promise<Centre> {
    return fetchApi<Centre>(`centres/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async updateCentreStatus(id: number, status: CentreStatus): Promise<Centre> {
    return fetchApi<Centre>(`centres/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  async deleteCentre(id: number): Promise<{ message: string; id: number; status: string }> {
    return fetchApi<{ message: string; id: number; status: string }>(`centres/${id}`, {
      method: 'DELETE',
    });
  },

  // Camera operations scoped under centres/{centreId}/cameras
  async getCameras(centreId: number): Promise<Camera[]> {
    return fetchApi<Camera[]>(`centres/${centreId}/cameras`, { cache: 'no-store' });
  },

  async getCamera(centreId: number, cameraId: number): Promise<Camera> {
    return fetchApi<Camera>(`centres/${centreId}/cameras/${cameraId}`, { cache: 'no-store' });
  },

  async createCamera(centreId: number, data: CameraCreateInput): Promise<Camera> {
    return fetchApi<Camera>(`centres/${centreId}/cameras`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateCamera(centreId: number, cameraId: number, data: CameraUpdateInput): Promise<Camera> {
    return fetchApi<Camera>(`centres/${centreId}/cameras/${cameraId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async updateCameraStatus(centreId: number, cameraId: number, is_active: boolean): Promise<Camera> {
    return fetchApi<Camera>(`centres/${centreId}/cameras/${cameraId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active }),
    });
  },
};
