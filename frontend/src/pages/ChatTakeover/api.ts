import { fetchWithAuth, resolveWebSocketUrl } from '../../app/apiClient';

export type TakeoverStatus = 'queued' | 'taken_over' | 'released' | 'resolved';
export type TakeoverPriority = 'critical' | 'high' | 'normal';

export interface TakeoverCase {
  id: string;
  patient_user_id: string;
  session_id: string;
  status: TakeoverStatus;
  priority: TakeoverPriority;
  workflow_status: string;
  summary: {
    patient_message?: string;
    patient_name?: string;
    patient_age?: number;
    patient_gender?: string;
    workflow_status?: string;
    ats_level?: number | null;
    suggested_department?: string | null;
    candidate_specialties?: Array<{ name?: string }>;
  };
  assigned_staff_id: string | null;
  claimed_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TakeoverMessage {
  id: string;
  case_id: string | null;
  author_type: 'patient' | 'assistant' | 'staff' | 'system';
  author_user_id: string | null;
  content: string;
  client_message_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface TakeoverCaseDetail {
  case: TakeoverCase;
  messages: TakeoverMessage[];
}

async function takeoverJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetchWithAuth(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || `Takeover request failed with HTTP ${response.status}`);
  }
  return (payload.data ?? payload) as T;
}

export const fetchTakeoverCases = (status?: TakeoverStatus, signal?: AbortSignal) =>
  takeoverJson<TakeoverCase[]>(`/staff/chat-takeover/cases${status ? `?status=${status}` : ''}`, { signal });

export const fetchTakeoverCase = (id: string, signal?: AbortSignal) =>
  takeoverJson<TakeoverCaseDetail>(`/staff/chat-takeover/cases/${encodeURIComponent(id)}`, { signal });

export const claimTakeoverCase = (id: string) =>
  takeoverJson<TakeoverCase>(`/staff/chat-takeover/cases/${encodeURIComponent(id)}/claim`, { method: 'POST' });

export const releaseTakeoverCase = (id: string) =>
  takeoverJson<TakeoverCase>(`/staff/chat-takeover/cases/${encodeURIComponent(id)}/release`, { method: 'POST' });

export const resolveTakeoverCase = (id: string) =>
  takeoverJson<TakeoverCase>(`/staff/chat-takeover/cases/${encodeURIComponent(id)}/resolve`, { method: 'POST' });

export const sendTakeoverMessage = (id: string, content: string, clientMessageId: string) =>
  takeoverJson<TakeoverMessage>(`/staff/chat-takeover/cases/${encodeURIComponent(id)}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, client_message_id: clientMessageId }),
  });

export function resolveTakeoverWebSocketUrl(sessionId?: string): string {
  const path = sessionId
    ? `/staff/chat-takeover/ws/${encodeURIComponent(sessionId)}`
    : '/staff/chat-takeover/ws/staff';
  return resolveWebSocketUrl(path);
}
