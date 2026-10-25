import { fetchApi } from './client';
import { LoginResponse, User } from '../types/user';

export const authApi = {
  /**
   * Authenticates user credentials with FastAPI backend.
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    return fetchApi<LoginResponse>('auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  /**
   * Retrieves current authenticated user profile using active JWT Bearer token.
   */
  async getMe(): Promise<User> {
    return fetchApi<User>('auth/me', { cache: 'no-store' });
  },
};
