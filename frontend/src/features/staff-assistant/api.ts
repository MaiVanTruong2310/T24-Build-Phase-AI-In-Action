import { fetchWithAuth } from '../../app/apiClient'

export interface PendingAction {
  id: string
  kind?: 'booking_review' | 'case_claim' | 'case_booking'
  booking_id?: string
  case_id?: string
  decision?: 'confirmed' | 'rejected'
  reason?: string | null
  case_summary?: Record<string, unknown>
  booking_summary?: Record<string, unknown>
  expires_at: string
}
export interface StaffAssistantReply {
  conversation_id: string
  assistant_text: string
  tool_states: { tool: string; status: string }[]
  pending_action: PendingAction | null
}
export interface StaffAssistantAlert {
  event_id: string
  case_id: string
  event_type: string
  reason: string
  created_at: string
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetchWithAuth(path, {
    method: body === undefined ? 'GET' : 'POST',
    ...(body !== undefined ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(payload.message || payload.detail || 'Không thể xử lý yêu cầu lúc này.') as Error & { status?: number }
    error.status = response.status
    throw error
  }
  return payload.data as T
}

export const sendStaffMessage = (message: string, conversation_id?: string) =>
  request<StaffAssistantReply>('/staff/assistant/chat', { message, ...(conversation_id ? { conversation_id } : {}) })

export const fetchStaffAssistantAlerts = (since?: string) => {
  const query = new URLSearchParams({ limit: '100' })
  if (since) query.set('since', since)
  return request<StaffAssistantAlert[]>(`/staff/workbench/assistant-alerts?${query}`)
}

export async function sendStaffMessageStream(
  message: string,
  conversationId: string | undefined,
  onToken: (token: string) => void,
  onToolState?: (toolState: { tool: string; status: string }) => void,
): Promise<StaffAssistantReply> {
  const response = await fetchWithAuth('/staff/assistant/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, ...(conversationId ? { conversation_id: conversationId } : {}) }),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload.message || payload.detail || 'Không thể xử lý yêu cầu lúc này.') as Error & { status?: number }
    error.status = response.status
    throw error
  }
  if (!response.body) {
    throw new Error('Không thể đọc dữ liệu phản hồi từ máy chủ.')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let reply: StaffAssistantReply = {
    conversation_id: conversationId || '',
    assistant_text: '',
    tool_states: [],
    pending_action: null,
  }
  let streamError: string | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let currentEvent = 'message'
    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        const raw = line.slice(5).trim()
        if (!raw) continue
        try {
          const parsed = JSON.parse(raw) as Record<string, unknown>
          if (currentEvent === 'token' && typeof parsed.token === 'string') {
            reply.assistant_text += parsed.token
            onToken(parsed.token)
          } else if (currentEvent === 'tool' && onToolState && typeof parsed.tool === 'string' && typeof parsed.status === 'string') {
            onToolState({ tool: parsed.tool, status: parsed.status })
          } else if (currentEvent === 'done') {
            reply = { ...reply, ...(parsed as unknown as StaffAssistantReply) }
          } else if (currentEvent === 'error') {
            streamError = typeof parsed.message === 'string' ? parsed.message : 'Không thể xử lý yêu cầu lúc này.'
          }
        } catch {
          // Ignore individual frame parse errors
        }
      }
    }
  }
  if (streamError) throw new Error(streamError)
  return reply
}

export const confirmStaffAction = (conversation_id: string, pending_action_id: string, patient_agreed = false) =>
  request<{ conversation_id: string; assistant_text: string }>('/staff/assistant/chat/confirm', { conversation_id, pending_action_id, patient_agreed })
export const cancelStaffAction = (conversation_id: string, pending_action_id: string) =>
  request<{ conversation_id: string; assistant_text: string }>('/staff/assistant/chat/cancel', { conversation_id, pending_action_id })
