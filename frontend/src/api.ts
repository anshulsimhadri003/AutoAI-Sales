import type { Appointment, DashboardOverview, Lead, ScoreBreakdown, Sequence, TimelineItem, WorkerConfig } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8400';
const DEALERSHIP_ID = import.meta.env.VITE_DEALERSHIP_ID || 'dealer-001';
const SITE_API_KEY = import.meta.env.VITE_SITE_API_KEY || '';

class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  headers.set('X-Dealership-ID', DEALERSHIP_ID);
  if (SITE_API_KEY) headers.set('X-API-Key', SITE_API_KEY);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const isJson = response.headers.get('content-type')?.includes('application/json');
  const body = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof body === 'object' && body && 'detail' in body ? String((body as { detail: unknown }).detail) : response.statusText;
    throw new ApiError(message, response.status, body);
  }
  return body as T;
}

export const api = {
  meta: { API_BASE_URL, DEALERSHIP_ID },
  health: () => request<string>('/health'),
  workers: () => request<WorkerConfig[]>('/api/v1/workers'),
  overview: () => request<DashboardOverview>('/api/v1/dashboard/overview'),
  leads: () => request<Lead[]>('/api/v1/leads'),
  lead: (id: string) => request<Lead>(`/api/v1/leads/${id}`),
  timeline: (id: string) => request<TimelineItem[]>(`/api/v1/leads/${id}/timeline`),
  scoreBreakdown: (id: string) => request<ScoreBreakdown>(`/api/v1/leads/${id}/score-breakdown`),
  createLead: (payload: Record<string, unknown>) => request<Lead>('/api/v1/leads', { method: 'POST', body: JSON.stringify(payload) }),
  respondToLead: (id: string, payload: { channel: string; message: string }) => request<Lead>(`/api/v1/leads/${id}/respond`, { method: 'POST', body: JSON.stringify(payload) }),
  assignLead: (id: string, payload: { rep_id: string; rep_name: string }) => request<Lead>(`/api/v1/leads/${id}/assign`, { method: 'POST', body: JSON.stringify(payload) }),
  sequences: () => request<Sequence[]>('/api/v1/sequences'),
  appointments: () => request<Appointment[]>('/api/v1/appointments'),
  slots: (vehicleId: string, date: string) => request<Array<{ start: string; end: string }>>(`/api/v1/appointments/slots?vehicle_id=${encodeURIComponent(vehicleId)}&date=${encodeURIComponent(date)}`),
  bookAppointment: (payload: Record<string, unknown>) => request<Appointment>('/api/v1/appointments/book', { method: 'POST', body: JSON.stringify(payload) }),
  markShow: (id: string) => request<Appointment>(`/api/v1/appointments/${id}/mark-show`, { method: 'POST' }),
  markNoShow: (id: string) => request<Appointment>(`/api/v1/appointments/${id}/mark-no-show`, { method: 'POST' }),
  aiReply: (payload: { lead_id?: string; message: string }) => request<{ reply: string }>('/api/v1/messages/reply', { method: 'POST', body: JSON.stringify(payload) }),
  leadEvent: (payload: Record<string, unknown>) => request<Record<string, unknown>>('/api/lead/event', { method: 'POST', body: JSON.stringify(payload) }),
  sessionEvents: (sessionId: string) => request<Record<string, unknown>[]>(`/api/lead/event/session/${encodeURIComponent(sessionId)}`)
};

export { ApiError };
