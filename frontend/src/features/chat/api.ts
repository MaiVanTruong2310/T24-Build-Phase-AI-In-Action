import { fetchPublicApi } from '../../app/apiClient';

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

export interface BookingIntake {
  required?: boolean;
  endpoint?: string;
  patient_name?: string;
  specialty_name?: string;
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
}

interface ChatResponse extends ChatMetadata {
  response: string;
}

interface StreamChatOptions {
  message: string;
  sessionId: string;
  signal?: AbortSignal;
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
  signal,
  onToken,
  onMetadata,
}: StreamChatOptions): Promise<void> {
  const response = await fetchPublicApi('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed with HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const consume = (rawEvent: string) => {
    const data = parseServerEvent(rawEvent);
    if (!data || data === '[DONE]') return;
    const event = JSON.parse(data) as ChatMetadata & { type?: string; content?: string; message?: string };
    if (event.type === 'token' && typeof event.content === 'string') {
      onToken(event.content);
    } else if (event.type === 'metadata') {
      onMetadata(event);
    } else if (event.type === 'error') {
      throw new Error(event.message || 'Chat stream failed');
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() || '';
    events.forEach(consume);
    if (done) break;
  }
  if (buffer.trim()) consume(buffer);
}

export async function sendChat(message: string, sessionId: string, signal?: AbortSignal): Promise<ChatResponse> {
  const response = await fetchPublicApi('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Chat request failed with HTTP ${response.status}`);
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

export async function submitBooking(
  endpoint: string,
  payload: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<{ saved: boolean; request_code: string; message: string }> {
  const response = await fetchPublicApi(endpoint, {
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
