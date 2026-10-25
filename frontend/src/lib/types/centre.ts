export type CentreStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';

export interface Centre {
  id: number;
  centre_code: string;
  name: string;
  location?: string | null;
  status: CentreStatus;
  camera_count: number;
  created_at: string;
  updated_at: string;
}

export interface CentreCreateInput {
  centre_code: string;
  name: string;
  location?: string | null;
  status?: CentreStatus;
}

export interface CentreUpdateInput {
  centre_code?: string;
  name?: string;
  location?: string | null;
  status?: CentreStatus;
}

export type CameraSourceType = 'VIDEO_FILE' | 'CAMERA';

export interface Camera {
  id: number;
  centre_id: number;
  name: string;
  source_type: CameraSourceType;
  source_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CameraCreateInput {
  name: string;
  source_type: CameraSourceType;
  source_url: string;
  is_active?: boolean;
}

export interface CameraUpdateInput {
  name?: string;
  source_type?: CameraSourceType;
  source_url?: string;
  is_active?: boolean;
}
