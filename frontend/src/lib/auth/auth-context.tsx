'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, LoginResponse } from '@/lib/types/user';
import { authApi } from '@/lib/api/auth';
import { setAuthToken, getAuthToken } from '@/lib/api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<LoginResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state from stored token
  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      const storedToken = getAuthToken();
      if (!storedToken) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const userData = await authApi.getMe();
        if (isMounted) {
          setToken(storedToken);
          setUser(userData);
        }
      } catch {
        if (isMounted) {
          setAuthToken(null);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void initializeAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<LoginResponse> => {
    const response = await authApi.login(email, password);
    setAuthToken(response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    return response;
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
