import type { ChatProfile } from './profile';
import { fetchPublicApi, fetchWithAuth, resolveWebSocketUrl } from '../../app/apiClient';
import { readAccessToken } from '../auth/session';

function fetchChatApi(url: string, options: RequestInit = {}) {
  return fetchWithAuth(url, options);
}
export interface SavedConversation { session_id: string; title: string; created_at: string; updated_at: string }
export interface SavedChatTurn { id: string; request_id: string; user_text: string; assistant_text: string | null; result: ChatMetadata | null; status: 'completed' | 'processing' | 'failed'; created_at: string }
export interface ConversationHistory { title: string; turns: SavedChatTurn[]; has_more: boolean }
export interface PatientTakeoverMessage { id: string; author_type: 'patient' | 'assistant' | 'staff' | 'system'; content: string; created_at: string }
export interface PatientTakeoverHistory { case: { id: string; status: string; session_id: string } | null; messages: PatientTakeoverMessage[] }
async function historyJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetchWithAuth(url, { signal });
  const data = await response.json();
  if (!response.ok) { const error = new Error(data.message || data.detail || 'Không thể tải lịch sử trò chuyện.') as Error & { status?: number }; error.status = response.status; throw error; }
  return data;
}
export const getConversations = (offset = 0, signal?: AbortSignal, patientProfileId?: string) => historyJson<{ conversations: SavedConversation[]; has_more: boolean }>(`/chat/conversations?offset=${offset}${patientProfileId ? "&patient_profile_id=" + encodeURIComponent(patientProfileId) : ""}`, signal);
export const getConversation = (id: string, offset = 0, signal?: AbortSignal) => historyJson<ConversationHistory>(`/chat/conversations/${encodeURIComponent(id)}?offset=${offset}`, signal);
export const getTakeoverConversation = (id: string, signal?: AbortSignal) => historyJson<PatientTakeoverHistory>(`/chat/conversations/${encodeURIComponent(id)}/takeover`, signal);


export async function deleteConversation(id: string): Promise<void> {
  const response = await fetchWithAuth(`/chat/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (response.status === 404) return;
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.message || data.detail || 'Không thể xóa cuộc trò chuyện.');
  }
}

export interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  tokens_saved?: number;
  model?: string;
  execution_mode?: string;
  estimated_cost_usd?: number;
}

export interface CandidateSpecialty {
  code?: string;
  name?: string;
  score?: number;
  reason?: string;
}

export interface BookingDoctor {
  id?: string;
  name?: string;
  title?: string;
}

export interface RankedSpecialtyItem {
  priority: number;
  department_name: string;
  department_code?: string;
  rationale?: string;
  target_symptoms?: string[];
  is_primary?: boolean;
}

export interface BookingIntake {
  required?: boolean;
  confirmed?: boolean;
  request_code?: string;
  endpoint?: string;
  booking_mode?: 'doctor' | 'package';
  patient_name?: string;
  patient_phone?: string;
  patient_email?: string;
  date_of_birth?: string;
  gender?: string;
  specialty_name?: string;
  specialty_code?: string;
  is_multi_specialty?: boolean;
  ranked_specialties?: RankedSpecialtyItem[];
  facility_preference?: string;
  preferred_date?: string;
  preferred_period?: string;
  patient_notes?: string;
  clinical_summary?: string;
  clinical_details?: {
    primary_complaint?: string;
    location?: string;
    severity?: string;
    pain_score?: number | null;
    duration?: string;
    associated?: string[];
    negatives?: string[];
  };
  missing_fields?: string[];
  is_authenticated?: boolean;
  selected_slot_id?: string | null;
  selected_doctor_id?: string | null;
  doctors?: BookingDoctor[];
}

export interface ChatMetadata {
  ats_level?: number | null;
  is_emergency?: boolean;
  quick_replies?: string[];
  suggested_department?: string | null;
  workflow_status?: string | null;
  token_usage?: TokenUsage | null;
  booking_intake?: BookingIntake | null;
  candidate_specialties?: CandidateSpecialty[];
  conflict_reason?: string | null;
  acuity_status?: string | null;
  disposition?: string | null;
  elapsed_ms?: number | null;
}

interface ChatResponse extends ChatMetadata {
  response: string;
}

interface StreamChatOptions {
  message: string;
  sessionId: string;
  patientProfileId?: string;
  requestId?: string;
  signal?: AbortSignal;
  profile?: ChatProfile;
  onToken: (token: string) => void;
  onMetadata: (metadata: ChatMetadata) => void;
}

function parseServerEvent(rawEvent: string): string | null {
  const data = rawEvent
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');
  return data || null;
}

export async function streamChat({
  message,
  sessionId,
  requestId,
  signal,
  onToken,
  onMetadata,
  profile,
  patientProfileId,
}: StreamChatOptions): Promise<void> {
  const response = await fetchChatApi('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, request_id: requestId, patient_profile: profile, patient_profile_id: patientProfileId }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed with HTTP ${response.status}`);
  }

  if (!response.headers.get('content-type')?.includes('text/event-stream')) {
    throw new Error('Chat endpoint did not return an event stream');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed = false;
  let content = '';

  const consume = (rawEvent: string) => {
    const data = parseServerEvent(rawEvent);
    if (!data) return;
    if (data === '[DONE]') {
      completed = true;
      return;
    }
    const event = JSON.parse(data) as ChatMetadata & { type?: string; content?: string; message?: string };
    if (event.type === 'token' && typeof event.content === 'string') {
      content += event.content;
      onToken(event.content);
    } else if (event.type === 'metadata') {
      onMetadata(event);
    } else if (event.type === 'error') {
      throw new Error(event.message || 'Chat stream failed');
    }
  };

  try {
    while (!completed) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() || '';
      events.forEach(consume);
      if (done) break;
    }
    if (buffer.trim() && !completed) consume(buffer);
    if (!completed || !content.trim()) {
      throw new Error('Chat stream ended without a complete response');
    }
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

export async function sendChat(message: string, sessionId: string, signal?: AbortSignal, profile?: ChatProfile, requestId?: string, patientProfileId?: string): Promise<ChatResponse> {
  const response = await fetchChatApi('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, request_id: requestId, patient_profile: profile, patient_profile_id: patientProfileId }),
    signal,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Chat request failed with HTTP ${response.status}`);
  }
  if (typeof payload.response !== 'string' || !payload.response.trim()) {
    throw new Error('Chat endpoint returned an invalid response');
  }
  return payload as ChatResponse;
}

export async function checkAgentStatus(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetchPublicApi('/status', { signal });
    if (!response.ok) return false;
    const payload = await response.json();
    return payload.status === 'ready';
  } catch {
    return false;
  }
}

export function resolveChatTakeoverWebSocketUrl(sessionId: string): string {
  const token = readAccessToken();
  const query = token ? `?${new URLSearchParams({ token }).toString()}` : '';
  return resolveWebSocketUrl(`/staff/chat-takeover/ws/${encodeURIComponent(sessionId)}${query}`);
}

export async function submitBooking(
  endpoint: string,
  payload: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<{ saved: boolean; request_code: string; message: string }> {
  const response = await fetchChatApi(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !result.saved) {
    throw new Error(result.detail || 'Yêu cầu chưa được lưu.');
  }
  return result;
}
