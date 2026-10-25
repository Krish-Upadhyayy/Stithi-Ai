export type UserRole = 'ADMIN' | 'CENTRE_USER' | 'REVIEWER' | string;

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  centre_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
