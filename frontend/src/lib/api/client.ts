/**
 * Base API client with typed response handling, error isolation, and JWT Bearer attachment.
 */

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

let memoryToken: string | null = null;

export function setAuthToken(token: string | null) {
  memoryToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('sih_auth_token', token);
    } else {
      localStorage.removeItem('sih_auth_token');
    }
  }
}

export function getAuthToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof window !== 'undefined') {
    memoryToken = localStorage.getItem('sih_auth_token');
  }
  return memoryToken;
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}/${endpoint.replace(/^\//, '')}`;

  const token = getAuthToken();
  const defaultHeaders: Record<string, string> = {
    Accept: 'application/json',
  };

  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers as Record<string, string>),
      },
    });

    if (!response.ok) {
      let errorData: { detail?: string; message?: string } = {};
      try {
        errorData = (await response.json()) as { detail?: string; message?: string };
      } catch {
        errorData = { detail: response.statusText };
      }
      throw new ApiError(
        errorData.detail || errorData.message || `Request failed with status ${response.status}`,
        response.status,
        errorData
      );
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      throw error;
    }
    const message = error instanceof Error ? error.message : String(error);
    throw new ApiError(
      `Backend service unreachable at ${url}. Ensure the FastAPI server is running.`,
      0,
      { originalError: message }
    );
  }
}

export { BASE_URL };
