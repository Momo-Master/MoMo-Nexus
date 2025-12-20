import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
}

async function fetchApi<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export function useApi<T>(endpoint: string, options?: ApiOptions) {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const refetch = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetchApi<T>(endpoint, options);
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, [endpoint, options]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { ...state, refetch };
}

// Specific API hooks
export function useDevices() {
  return useApi<Device[]>('/fleet/devices');
}

export function useHandshakes() {
  return useApi<Handshake[]>('/captures/handshakes');
}

export function useCrackJobs() {
  return useApi<CrackJob[]>('/cloud/hashcat/jobs');
}

export function useStats() {
  return useApi<Stats>('/stats');
}

export function usePhishingSessions() {
  return useApi<PhishingSession[]>('/cloud/evilginx/sessions');
}

// Types (re-exported for convenience)
import type { Device, Handshake, CrackJob, Stats } from '../types';

export interface PhishingSession {
  id: string;
  phishlet: string;
  username: string;
  password: string;
  tokens: Record<string, string>;
  userAgent: string;
  remoteAddr: string;
  createTime: string;
  updateTime: string;
}

