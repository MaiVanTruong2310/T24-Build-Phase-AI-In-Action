import { PatientSelector, usePatientSelection } from '../features/patient-profiles/PatientSelector';
import { PatientUpdates, type PatientUpdatesHandle, type SupportRequestState } from '../features/coordinator/PatientUpdates';
import '../components/ChatMessageInput.css';
import '../components/ChatSendButton.css';
import { AIIdentity } from '../components/AIIdentity';
import { BookingDrawer } from '../features/chat/BookingDrawer';
import { ChatHistoryPanel } from '../features/chat/ChatHistoryPanel';
import { ChatAccessGate } from '../features/chat/ChatAccessGate';
import { GUEST_PROFILE_EVENT, readGuestProfile, saveGuestProfile, type ChatProfile } from '../features/chat/profile';
import { AssistantMessage } from '../features/chat/AssistantMessage';
import { AssistantTurnMetrics } from '../features/chat/AssistantTurnMetrics';
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  History,
  Headset,
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ClipboardList,
  LoaderCircle,
  Maximize2,
  Mic,
  Minimize2,
  Minus,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { closeChat, toggleChat, type RootState } from '../app/store';
import {
  getConversation,
  getTakeoverConversation,
  type SavedChatTurn,
  sendChat,
  streamChat,
  type BookingIntake,
  type ChatMetadata,
  resolveChatTakeoverWebSocketUrl,
} from '../features/chat/api';

interface ChatbotWidgetProps {
  embedded?: boolean;
}

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  time: string;
  pending?: boolean;
  error?: boolean;
  metadata?: ChatMetadata;
  staff?: boolean;
  elapsedMs?: number | null;
}

const DEFAULT_QUICK_REPLIES = [
  'Đau đầu, chóng mặt kéo dài',
  'Tức ngực, khó thở khi gắng sức',
  'Tư vấn khám sức khỏe tổng quát',
  'Đặt lịch khám Bác sĩ chuyên khoa',
];

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  sender: 'bot',
  text: 'Kính chào Quý bệnh nhân! Em là VgreenAI, trợ lý tư vấn thuộc hệ thống VCare+.\n\nBác vui lòng mô tả các triệu chứng hiện tại (vị trí đau, thời gian xuất hiện, mức độ khó chịu) để em hỗ trợ phân tầng mức ưu tiên và kết nối chuyên khoa phù hợp.',
  time: '',
};

function createSessionId(): string {
  const existing = sessionStorage.getItem('p124_chat_session_id');
  if (existing) return existing;
  const suffix = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const sessionId = `web-${suffix}`;
  sessionStorage.setItem('p124_chat_session_id', sessionId);
  return sessionId;
}

function savedMessages(turns: SavedChatTurn[]): Message[] {
  return turns.flatMap(turn => {
    const time = new Date(turn.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    return [
      { id: `${turn.id}-user`, sender: 'user' as const, text: turn.user_text, time },
      {
        id: `${turn.id}-bot`,
        sender: 'bot' as const,
        text: turn.assistant_text || 'Lượt chat chưa hoàn tất. Bạn có thể gửi lại tin nhắn.',
        time,
        error: turn.status !== 'completed',
        metadata: turn.result || undefined,
        elapsedMs: turn.result?.elapsed_ms ?? undefined,
      },
    ];
  });
}

function displayTime(): string {
  return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function shouldShowAts(metadata?: ChatMetadata): boolean {
  if (!metadata?.ats_level) return false;
  if (metadata.is_emergency) return true;
  return new Set([
    'PROBING_IN_PROGRESS',
    'SAFETY_REVIEW',
    'TRIAGED_AWAITING_SCHEDULE',
    'TRIAGED_READY_FOR_BOOKING',
  ]).has(metadata.workflow_status || '');
}

function AtsBadge({ metadata }: { metadata?: ChatMetadata }) {
  if (!shouldShowAts(metadata)) return null;
  const level = metadata?.ats_level;
  const emergency = metadata?.is_emergency;

  if (emergency || (level && level <= 2)) {
    return (
      <div className="mb-2.5 inline-flex items-center gap-1.5 rounded-full bg-red-500/15 border border-red-500/30 px-3 py-1 text-[11px] font-bold text-red-600 dark:text-red-400 shadow-sm animate-pulse">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
        <span>ATS {level || 2} · Cấp Cứu Khẩn Cấp (Ưu Tiên 1)</span>
      </div>
    );
  }
  if (level === 3) {
    return (
      <div className="mb-2.5 inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 px-3 py-1 text-[11px] font-bold text-amber-700 dark:text-amber-400 shadow-sm">
        <Activity className="h-3 w-3" />
        <span>ATS 3 · Khám Trong Ngày (Ưu Tiên Cao)</span>
      </div>
    );
  }
  if (level === 4) {
    return (
      <div className="mb-2.5 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-[11px] font-bold text-emerald-700 dark:text-emerald-400 shadow-sm">
        <CheckCircle2 className="h-3 w-3" />
        <span>ATS 4 · Khám Sớm / Hẹn Khám Bác Sĩ</span>
      </div>
    );
  }
  return (
    <div className="mb-2.5 inline-flex items-center gap-1.5 rounded-full bg-blue-500/15 border border-blue-500/30 px-3 py-1 text-[11px] font-bold text-blue-700 dark:text-cyan-400 shadow-sm">
      <Bot className="h-3 w-3" />
      <span>ATS 5 · Tư Vấn Y Khoa Tiêu Chuẩn</span>
    </div>
  );
}

export function ChatbotWidget({ embedded = false }: ChatbotWidgetProps) {
  const dispatch = useDispatch();
  const floatingChatOpen = useSelector((state: RootState) => state.layout.isChatOpen);
  const authUser = useSelector((state: RootState) => state.auth.user);
  const patientSelection = usePatientSelection();
  const [guestProfile, setGuestProfile] = useState<ChatProfile | null>(readGuestProfile);
  const profile: ChatProfile | null = authUser
    ? { name: patientSelection.selectedProfile?.full_name || authUser.full_name, phone: patientSelection.selectedProfile?.contact_phone || authUser.phone || '' }
    : guestProfile;
  const chatLocked = !authUser && !guestProfile;
  const ownerKey = authUser ? `user:${authUser.id}:profile:${patientSelection.profileId || "self"}` : guestProfile ? `guest:${guestProfile.name}:${guestProfile.phone}` : '';
  const isChatOpen = embedded || floatingChatOpen;
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isSending, setIsSending] = useState(false);
  const [sessionId, setSessionId] = useState(createSessionId);
  const supportRef = useRef<PatientUpdatesHandle>(null);
  const [supportState, setSupportState] = useState<SupportRequestState>({ busy: false, requested: false, control: 'ai' });
  const [isBookingDrawerOpen, setIsBookingDrawerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyDeleting, setHistoryDeleting] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyMore, setHistoryMore] = useState(false);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyReload, setHistoryReload] = useState(0);
  const historyRequest = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const activeRequest = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback((smooth = false) => {
    const container = messagesContainerRef.current;
    if (container) {
      if (smooth) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth',
        });
      } else {
        container.scrollTop = container.scrollHeight;
      }
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    }
  }, []);

  const handleMessagesScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const threshold = 120;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
    isNearBottomRef.current = isAtBottom;
  }, []);

  const ensureChatVisibleInPage = useCallback(() => {
    if (!embedded || !inputRef.current) return;
    const rect = inputRef.current.getBoundingClientRect();
    if (rect.bottom > window.innerHeight - 10) {
      window.scrollBy({
        top: rect.bottom - window.innerHeight + 30,
        behavior: 'smooth',
      });
    }
  }, [embedded]);

  useEffect(() => {
    if (!isChatOpen) return;
    if (isNearBottomRef.current) {
      scrollToBottom(false);
    }
  }, [messages, isChatOpen, scrollToBottom]);

  useEffect(() => {
    if (isChatOpen) {
      isNearBottomRef.current = true;
      const timer = setTimeout(() => scrollToBottom(false), 80);
      return () => clearTimeout(timer);
    }
  }, [isChatOpen, scrollToBottom]);

  useEffect(() => {
    if (isChatOpen && !embedded) {
      inputRef.current?.focus();
    }
  }, [isChatOpen, embedded]);

  useEffect(() => () => activeRequest.current?.abort(), []);

  useEffect(() => {
    const refreshGuest = () => setGuestProfile(readGuestProfile());
    window.addEventListener(GUEST_PROFILE_EVENT, refreshGuest);
    return () => window.removeEventListener(GUEST_PROFILE_EVENT, refreshGuest);
  }, []);

  useEffect(() => {
    if (authUser && readGuestProfile()) saveGuestProfile(null);
  }, [authUser]);

  useEffect(() => {
    const previousOwner = sessionStorage.getItem('p124_chat_owner') || '';
    if (previousOwner === ownerKey) {
      // Floating and embedded chat widgets must share the same owner/session.
      const sharedSession = sessionStorage.getItem('p124_chat_session_id');
      if (sharedSession) setSessionId(sharedSession);
      activeRequest.current?.abort();
      activeRequest.current = null;
      setMessages([WELCOME_MESSAGE]);
      setInputText('');
      setIsSending(false);
      return;
    }
    activeRequest.current?.abort();
    activeRequest.current = null;
    const next = `web-${crypto.randomUUID?.() || Date.now()}`;
    sessionStorage.setItem('p124_chat_session_id', next);
    sessionStorage.setItem('p124_chat_owner', ownerKey);
    setSessionId(next);
    setMessages([WELCOME_MESSAGE]);
    setInputText('');
    setIsSending(false);
  }, [ownerKey]);

  useEffect(() => {
    if (!authUser?.id || !isChatOpen) { setHistoryError(''); setHistoryMore(false); setHistoryLoading(false); return; }
    const controller = new AbortController();
    historyRequest.current?.abort(); historyRequest.current = controller;
    setHistoryLoading(true); setHistoryError('');
    getConversation(sessionId, 0, controller.signal).then(async data => {
      if (controller.signal.aborted) return;
      const takeover = await getTakeoverConversation(sessionId, controller.signal).catch(() => null);
      if (controller.signal.aborted) return;
      const archived = savedMessages(data.turns);
      const staffMessages = (takeover?.messages || [])
        .filter(message => message.author_type === 'staff')
        .map(message => ({
          id: `takeover-${message.id}`,
          sender: 'bot' as const,
          staff: true,
          text: message.content,
          time: new Date(message.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        }));
      setMessages([...archived, ...staffMessages].length ? [...archived, ...staffMessages] : [WELCOME_MESSAGE]);
      setHistoryMore(data.has_more); setHistoryOffset(data.turns.length);
    }).catch((error: Error & { status?: number }) => {
      if (controller.signal.aborted) return;
      if (error.status === 404) { setMessages([WELCOME_MESSAGE]); setHistoryMore(false); setHistoryOffset(0); }
      else setHistoryError(error.message || 'Không thể tải lịch sử.');
    }).finally(() => { if (!controller.signal.aborted) setHistoryLoading(false); });
    return () => controller.abort();
  }, [sessionId, ownerKey, authUser?.id, isChatOpen, historyReload]);

  useEffect(() => {
    if (!authUser?.id || !isChatOpen) return undefined;
    let stopped = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(resolveChatTakeoverWebSocketUrl(sessionId));
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string;
            message?: { id?: string; content?: string; created_at?: string; author_type?: string };
          };
          const message = payload.message;
          const content = message?.content;
          if (payload.type !== 'takeover.message_created' || !message?.id || typeof content !== 'string' || message.author_type !== 'staff') return;
          setMessages((current) => {
            if (current.some((item) => item.id === `takeover-${message.id}`)) return current;
            return [...current, {
              id: `takeover-${message.id}`,
              sender: 'bot',
              staff: true,
              text: content,
              time: message.created_at ? new Date(message.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : displayTime(),
            }];
          });
        } catch {
          // Ignore malformed realtime events; durable history remains authoritative.
        }
      };
      socket.onclose = () => {
        if (!stopped) reconnectTimer = window.setTimeout(connect, 5000);
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [authUser?.id, isChatOpen, sessionId]);

  const loadOlderMessages = async () => {
    const controller = new AbortController(); historyRequest.current?.abort(); historyRequest.current = controller;
    setHistoryLoading(true); setHistoryError('');
    try {
      const data = await getConversation(sessionId, historyOffset, controller.signal);
      if (controller.signal.aborted) return;
      setMessages(current => [...savedMessages(data.turns), ...current.filter(message => message.id !== 'welcome')].filter((message,index,all) => all.findIndex(item => item.id === message.id) === index));
      setHistoryMore(data.has_more); setHistoryOffset(value => value + data.turns.length);
    } catch (error) { if (!controller.signal.aborted) setHistoryError(error instanceof Error ? error.message : 'Không thể tải lịch sử.'); }
    finally { if (!controller.signal.aborted) setHistoryLoading(false); }
  };

  const openConversation = (id: string) => {
    if (isSending || historyDeleting || historyLoading) return;
    sessionStorage.setItem('p124_chat_session_id', id); setSessionId(id);
    setHistoryOpen(false); setMessages([WELCOME_MESSAGE]); setHistoryError(''); setInputText('');
    if (id === sessionId) setHistoryReload(value => value + 1);
  };

  const resetConversation = () => {
    activeRequest.current?.abort();
    const next = `web-${crypto.randomUUID?.() || Date.now()}`;
    sessionStorage.setItem('p124_chat_session_id', next);
    setSessionId(next);
    setMessages([WELCOME_MESSAGE]);
    setInputText('');
    setIsSending(false);
  };

  const updateBot = (id: string, update: Partial<Message> | ((current: Message) => Partial<Message>)) => {
    setMessages((current) =>
      current.map((message) => {
        if (message.id !== id) return message;
        const next = typeof update === 'function' ? update(message) : update;
        return { ...message, ...next };
      })
    );
  };

  const sendMessage = async (rawText: string) => {
    const text = rawText.trim();
    if (!text || isSending || historyDeleting || chatLocked || historyLoading || historyError) return;

    const request = new AbortController();
    activeRequest.current = request;
    setIsSending(true);
    setInputText('');
    const stamp = Date.now();
    const botId = `bot-${stamp}`;
    const requestId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: `user-${stamp}`, sender: 'user', text, time: displayTime() },
      { id: botId, sender: 'bot', text: '', time: displayTime(), pending: true },
    ]);
    isNearBottomRef.current = true;
    setTimeout(() => {
      scrollToBottom(true);
      ensureChatVisibleInPage();
    }, 40);

    setHistoryOpen(false);
    let completed = false;
    let streamedText = '';
    let receivedMetadata = false;
    const sendStartTime = Date.now();
    let recordedElapsedMs: number | undefined;

    const showConnectionError = () => {
      updateBot(botId, {
        text: 'Không thể nhận phản hồi từ trợ lý. Vui lòng kiểm tra kết nối hoặc thử lại sau.',
        pending: false,
        error: true,
        metadata: undefined,
      });
      setTimeout(() => {
        if (isNearBottomRef.current) scrollToBottom(true);
      }, 50);
    };
    try {
      await streamChat({
        message: text,
        requestId,
        patientProfileId: patientSelection.profileId || undefined,
        profile: profile || undefined,
        sessionId,
        signal: request.signal,
        onToken: (token) => {
          streamedText += token;
          updateBot(botId, { text: streamedText, pending: false });
          if (isNearBottomRef.current) {
            scrollToBottom(false);
          }
        },
        onMetadata: (metadata) => {
          receivedMetadata = true;
          const currentElapsed = metadata.elapsed_ms ?? (Date.now() - sendStartTime);
          recordedElapsedMs = currentElapsed;
          updateBot(botId, {
            metadata: {
              ...metadata,
              elapsed_ms: currentElapsed,
            },
            elapsedMs: currentElapsed,
          });
          if (metadata.booking_intake?.required) {
            setIsBookingDrawerOpen(true);
          }
        },
      });
      completed = true;
      const finalElapsed = recordedElapsedMs ?? (Date.now() - sendStartTime);
      updateBot(botId, (current) => ({
        pending: false,
        elapsedMs: current.elapsedMs ?? finalElapsed,
        metadata: current.metadata
          ? { ...current.metadata, elapsed_ms: current.metadata.elapsed_ms ?? finalElapsed }
          : undefined,
      }));
      setTimeout(() => {
        if (isNearBottomRef.current) {
          scrollToBottom(true);
        }
      }, 60);
    } catch {
      if (request.signal.aborted) return;
      // Do not replay a turn after the server has already begun responding.
      if (streamedText || receivedMetadata) {
        showConnectionError();
        return;
      }
      try {
        const result = await sendChat(text, sessionId, request.signal, profile || undefined, requestId, patientSelection.profileId || undefined);
        completed = true;
        const finalElapsed = result.elapsed_ms ?? (Date.now() - sendStartTime);
        updateBot(botId, {
          text: result.response,
          pending: false,
          metadata: { ...result, elapsed_ms: finalElapsed },
          elapsedMs: finalElapsed,
        });
        if (result.booking_intake?.required) {
          setIsBookingDrawerOpen(true);
        }
        setTimeout(() => {
          if (isNearBottomRef.current) {
            scrollToBottom(true);
          }
        }, 60);
      } catch {
        if (!request.signal.aborted) showConnectionError();
      }
    } finally {
      if (completed && authUser) setHistoryOffset(value => value + 1);
      if (activeRequest.current === request) {
        activeRequest.current = null;
        setIsSending(false);
      }
    }
  };

  const rawIntake = [...messages]
    .reverse()
    .find((message) => message.sender === 'bot' && message.metadata?.booking_intake)
    ?.metadata?.booking_intake;

  const latestBookingIntake: BookingIntake = rawIntake
    ? {
        ...rawIntake,
        date_of_birth: rawIntake.date_of_birth || authUser?.date_of_birth || '',
        gender: rawIntake.gender || authUser?.gender || '',
        is_authenticated: Boolean(authUser),
      }
    : {
        required: true,
        patient_name: profile?.name || '',
        patient_phone: profile?.phone || '',
        date_of_birth: authUser?.date_of_birth || profile?.date_of_birth || '',
        gender: authUser?.gender || profile?.gender || 'male',
        is_authenticated: Boolean(authUser),
      };

  const handleBookingSubmitted = useCallback((requestCode: string) => {
    setMessages((current) => [
      ...current,
      {
        id: `system-${Date.now()}`,
        sender: 'bot',
        text: `✓ **Đã tiếp nhận yêu cầu đặt khám thành công!**\nMã tiếp nhận của bác là: **${requestCode}**.\nĐiều phối viên y tế sẽ sớm liên hệ theo số điện thoại đã cung cấp để hỗ trợ hoàn tất lịch khám cho bác.`,
        time: displayTime(),
      },
    ]);
  }, []);

  const latestQuickReplies =
    [...messages]
      .reverse()
      .find((message) => message.sender === 'bot' && message.metadata?.quick_replies?.length)
      ?.metadata?.quick_replies || DEFAULT_QUICK_REPLIES;
  const supportLabel = supportState.control === 'human'
    ? 'Đang kết nối bác sĩ'
    : supportState.requested ? 'Đã gửi yêu cầu' : 'Yêu cầu hỗ trợ';

  return (
    <div
      className={
        embedded
          ? 'flex h-full min-h-[640px] w-full flex-col'
          : 'fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[9999] flex flex-col items-end pointer-events-none'
      }
    >
      {/* ─── CHAT WINDOW MODAL / EMBEDDED CONTAINER ─── */}
      {isChatOpen && (
        <section
          className={`flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800/90 bg-white/95 dark:bg-[#0B1329]/95 backdrop-blur-2xl transition-all duration-300 pointer-events-auto ${
            embedded
              ? 'h-full min-h-[660px] w-full shadow-lg dark:shadow-2xl'
              : isExpanded
              ? 'h-[88vh] w-[min(48rem,calc(100vw-2rem))] shadow-2xl shadow-blue-950/25 dark:shadow-cyan-950/40 ring-1 ring-blue-500/10 dark:ring-cyan-500/20'
              : 'h-[min(744px,calc(100dvh-2rem))] w-[min(32.5rem,calc(100vw-1.5rem))] shadow-2xl shadow-blue-950/20 dark:shadow-black/60 ring-1 ring-blue-500/10 dark:ring-cyan-500/20'
          }`}
          aria-label="P-124 Medical Assistant"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#d5e8de] dark:border-white/10 bg-gradient-to-r from-[#edf7f1] via-[#f6fcf9] to-[#edf7f1] dark:from-[#0B1329] dark:via-[#0E2046] dark:to-[#0B1329] px-4 py-3.5 text-[#295c49] dark:text-white">
            <div className="flex items-center gap-3">
              <div className="flex min-w-0 flex-col gap-2">
                <AIIdentity />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-1 text-[#527565] dark:text-slate-300">
              <button
                type="button"
                disabled={chatLocked || supportState.busy || supportState.requested || supportState.control === 'human'}
                aria-label={supportLabel}
                title={supportLabel}
                onClick={() => supportRef.current?.requestHuman()}
                className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-medium hover:bg-emerald-100 dark:hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Headset className="h-4 w-4 shrink-0" />
                <span className={embedded ? 'hidden sm:inline' : 'sr-only'}>{supportLabel}</span>
              </button>
              {authUser && <button type="button" disabled={isSending || historyDeleting || historyLoading} aria-label="Lịch sử trò chuyện" title="Lịch sử trò chuyện" onClick={() => setHistoryOpen(value => !value)} className="rounded-lg p-2 hover:bg-emerald-100 dark:hover:bg-white/10 disabled:opacity-50"><History className="h-4 w-4" /></button>}
              <button
                type="button"
                onClick={() => setIsBookingDrawerOpen((prev) => !prev)}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-[#28785c] dark:text-cyan-200 hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white transition-colors cursor-pointer"
                title="Mở phiếu hẹn khám bác sĩ chuyên khoa"
              >
                <ClipboardList className="h-3.5 w-3.5 text-cyan-400" />
                <span className="hidden sm:inline">Phiếu khám</span>
              </button>
              <button
                type="button"
                onClick={resetConversation}
                className="rounded-lg p-1.5 transition-colors hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white cursor-pointer"
                title="Tạo cuộc hội chẩn mới"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
              {!embedded && (
                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="hidden sm:inline-flex rounded-lg p-1.5 transition-colors hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white cursor-pointer"
                  title={isExpanded ? 'Thu nhỏ' : 'Mở rộng'}
                >
                  {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </button>
              )}
              {!embedded && (
                <button
                  type="button"
                  onClick={() => dispatch(closeChat())}
                  className="rounded-lg p-1.5 transition-colors hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white cursor-pointer"
                  title="Đóng cửa sổ chat"
                >
                  <Minus className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          <div className="relative flex min-h-0 flex-1 flex-col">
          <div inert={chatLocked} aria-hidden={chatLocked || undefined} className={`flex min-h-0 flex-1 flex-col ${chatLocked ? 'pointer-events-none select-none blur-sm' : ''}`}>
          {/* Message List */}
          <PatientSelector selection={patientSelection} disabled={isSending || historyLoading} />
          {authUser && historyOpen && <ChatHistoryPanel patientProfileId={patientSelection.profileId || undefined} key={authUser.id + patientSelection.profileId} activeSessionId={sessionId} onSelect={openConversation} busy={isSending || historyLoading} onDeletingChange={setHistoryDeleting} onDeleted={id => { if (id === sessionId) { historyRequest.current?.abort(); setHistoryError(''); setHistoryMore(false); setHistoryOffset(0); resetConversation(); } }} />}
          {authUser && <p className="border-b border-slate-100 px-4 py-2 text-[11px] text-slate-500 dark:border-slate-800">Hồ sơ người khám đang chọn · Hội thoại được tách riêng theo người khám.</p>}
          {historyError && <p role="alert" className="px-4 py-2 text-xs text-red-600">{historyError} <button type="button" onClick={() => setHistoryReload(value => value + 1)} className="underline">Thử tải lại</button></p>}
          {historyLoading && <p className="px-4 py-2 text-xs text-slate-500">Đang tải cuộc trò chuyện…</p>}
          {historyMore && <button disabled={historyLoading || isSending} type="button" onClick={loadOlderMessages} className="px-4 py-2 text-xs text-blue-600">Tải tin nhắn cũ hơn</button>}
          <div
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
            className="flex-1 space-y-4 overflow-y-auto bg-[#f6fcf9] dark:bg-[#080E1F]/90 p-4 text-xs transition-colors scroll-smooth"
            aria-live="polite"
          >
            {messages.map((message) => {
              const candidates = message.metadata?.candidate_specialties || [];
              const isUser = message.sender === 'user';

              return (
                <div key={message.id} className={isUser ? 'flex justify-end' : 'flex items-start gap-2.5'}>
                  {!isUser && (
                    <span className="mt-1 shrink-0"><AIIdentity avatarOnly /></span>
                  )}

                  <div
                    className={`${
                      isUser
                        ? 'max-w-[85%] rounded-2xl rounded-tr-xs bg-gradient-to-r from-[#37856a] to-[#296c55] dark:from-blue-600 dark:to-blue-700 px-4 py-3 text-white shadow-md shadow-emerald-900/10 dark:shadow-blue-600/20'
                        : `max-w-[90%] rounded-2xl rounded-tl-xs border bg-white dark:bg-[#0F1B35] p-4 shadow-sm text-slate-800 dark:text-slate-100 ${
                            message.error
                              ? 'border-red-200 dark:border-red-900/50'
                              : 'border-slate-200/90 dark:border-slate-800/90'
                          }`
                    }`}
                  >
                    {/* Doctor Supervision Stamp on Bot Messages */}
                    {!isUser && (
                      <div className="mb-2 flex items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-1.5">
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                          {message.staff ? 'Nhân viên y tế' : 'Trợ lý AI'}
                          VgreenAI
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                          {message.time || displayTime()}
                        </span>
                      </div>
                    )}

                    {/* ATS Triage Badge */}
                    {!isUser && <AtsBadge metadata={message.metadata} />}

                    {/* Content */}
                    {message.pending && !message.text ? (
                      <div className="flex items-center gap-2.5 py-1 text-slate-500 dark:text-slate-400 font-medium">
                        <LoaderCircle className="h-4 w-4 animate-spin text-blue-500 dark:text-cyan-400" />
                        <span>Đang chờ phản hồi từ trợ lý…</span>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap break-words leading-relaxed text-xs sm:text-[13px]">
                        {isUser ? message.text : <AssistantMessage text={message.text} />}
                      </div>
                    )}

                    {/* Small telemetry info under medical disclaimer */}
                    {!isUser && !message.pending && message.id !== 'welcome' && message.text && (
                      <AssistantTurnMetrics
                        tokenUsage={message.metadata?.token_usage}
                        elapsedMs={message.elapsedMs ?? message.metadata?.elapsed_ms}
                        text={message.text}
                      />
                    )}

                    {/* Candidate Specialties Card */}
                    {candidates.length > 0 && (
                      <div className="mt-3 rounded-xl border border-[#cde5d7] dark:border-blue-900/60 bg-[#edf7f1] dark:bg-[#0c1830] p-3 text-[11px] text-[#295c49] dark:text-cyan-200">
                        <div className="flex items-center gap-1 font-bold text-[#295c49] dark:text-cyan-300 mb-1.5">
                          <Sparkles className="h-3.5 w-3.5 text-blue-600 dark:text-cyan-400" />
                          <span>Chuyên khoa gợi ý đối chiếu:</span>
                        </div>
                        <div className="space-y-1">
                          {candidates.slice(0, 3).map((candidate) => (
                            <div key={candidate.code || candidate.name} className="flex items-start gap-1.5">
                              <span className="text-blue-500 dark:text-cyan-400">•</span>
                              <span>
                                <strong className="font-semibold text-slate-900 dark:text-white">
                                  {candidate.name || candidate.code}
                                </strong>
                                {candidate.reason ? `: ${candidate.reason}` : ''}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Conflict Warning */}
                    {message.metadata?.conflict_reason && (
                      <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/40 p-2.5 text-[11px] text-amber-800 dark:text-amber-300">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                        <span>{message.metadata.conflict_reason}</span>
                      </div>
                    )}


                    {/* User timestamp */}
                    {isUser && message.time && (
                      <p className="mt-1 text-right text-[10px] text-blue-100/80">{message.time}</p>
                    )}
                  </div>
                </div>
              );
            })}
            <PatientUpdates
              key={ownerKey + sessionId}
              ref={supportRef}
              sessionId={sessionId}
              owner={ownerKey}
              showRequestButton={false}
              onSupportStateChange={setSupportState}
            />
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Reply Suggestions */}
          {latestQuickReplies.length > 0 && (
            <div className="flex gap-2 overflow-x-auto border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-[#0B1329]/95 px-3.5 py-2.5 no-scrollbar">
              {latestQuickReplies.slice(0, 4).map((reply) => (
                <button
                  key={reply}
                  type="button"
                  disabled={isSending || historyDeleting || historyLoading || Boolean(historyError)}
                  onClick={() => {
                    void sendMessage(reply);
                    ensureChatVisibleInPage();
                  }}
                  className="whitespace-nowrap rounded-full border border-[#cde5d7] dark:border-slate-700/80 bg-[#f6fcf9] dark:bg-slate-800/90 px-3 py-1.5 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-emerald-500 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:border-cyan-400 dark:hover:bg-slate-700 dark:hover:text-cyan-300 disabled:opacity-50 transition-all shadow-xs cursor-pointer active:scale-95 shrink-0"
                >
                  {reply}
                </button>
              ))}
            </div>
          )}

          {/* Input & Action Bar */}
          <div className="border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-[#0B1329]/95 p-3 backdrop-blur-md">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void sendMessage(inputText);
                ensureChatVisibleInPage();
              }}
              className="flex items-center gap-2"
            >
              <div className="chat-message-input-container">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  disabled={isSending || historyDeleting || historyLoading || Boolean(historyError)}
                  onFocus={ensureChatVisibleInPage}
                  onChange={(event) => setInputText(event.target.value)}
                  placeholder="Mô tả triệu chứng, vị trí và thời gian bắt đầu…"
                  aria-label="Nội dung tin nhắn"
                    className="chat-message-input"
                />
              </div>
                <button
                  type="button"
                  disabled
                  className="chat-message-input-mic"
                    aria-label="Nhập bằng giọng nói (sắp ra mắt)"
                  title="Tính năng nhập giọng nói sắp ra mắt"
                >
                  <Mic className="h-4 w-4" />
                </button>

              <button
                type="submit"
                disabled={isSending || historyDeleting || historyLoading || Boolean(historyError) || !inputText.trim()}
                className="chat-send-button"
                aria-label="Gửi tin nhắn"
              >
                  <span>Gửi</span>
                  <span className="chat-send-button__icon" aria-hidden="true">
                    {isSending ? (
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                    ) : (
                      <svg height="24" width="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M0 0h24v24H0z" fill="none" />
                        <path d="M16.172 11l-5.364-5.364 1.414-1.414L20 12l-7.778 7.778-1.414-1.414L16.172 13H4v-2z" fill="currentColor" />
                      </svg>
                    )}
                  </span>
                </button>
            </form>

            <p className="mt-2 text-center text-[10px] text-slate-400 dark:text-slate-500">
              P-124 hỗ trợ tư vấn sơ bộ. Với triệu chứng nguy cấp, xin vui lòng gọi{' '}
              <a href="tel:115" className="font-bold text-red-500 dark:text-red-400 hover:underline">
                115
              </a>{' '}
              ngay.
            </p>
          </div>
          </div>
          {chatLocked && <ChatAccessGate onGuest={saveGuestProfile} />}
          </div>
        </section>
      )}

      {isChatOpen && !chatLocked && (
        <BookingDrawer
          open={isBookingDrawerOpen}
          onOpenChange={setIsBookingDrawerOpen}
          patientProfileId={patientSelection.profileId || undefined}
          selectedPatient={patientSelection.selectedProfile}
          intake={latestBookingIntake}
          sessionId={sessionId}
          onSubmitted={handleBookingSubmitted}
        />
      )}

      {/* ─── FLOATING ACTION BUTTON (FAB) TRIGGER ─── */}
      {!embedded && !isChatOpen && (
        <div className="animate-gentle-float pointer-events-auto">
          <button
            type="button"
            onClick={() => dispatch(toggleChat())}
            className="group relative flex items-center gap-3 rounded-full border border-blue-200/90 dark:border-cyan-500/35 bg-white/95 dark:bg-[#0B1329]/95 backdrop-blur-xl py-2.5 pl-4 pr-3 shadow-xl dark:shadow-2xl shadow-blue-900/10 dark:shadow-cyan-500/15 hover:shadow-2xl hover:shadow-blue-500/30 dark:hover:shadow-cyan-400/25 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer ring-1 ring-blue-500/10 dark:ring-cyan-400/20"
            aria-label="Mở VgreenAI · AI Vip Pro Max"
          >
            {/* Live Pulsing Dot */}
            <div className="relative flex h-3 w-3 shrink-0 items-center justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 shadow-sm shadow-emerald-500/60" />
            </div>

            {/* Doctor supervision label */}
            <div className="flex flex-col text-left pr-0.5">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-cyan-300 transition-colors">
                  VgreenAI
                </span>
                <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-blue-50 dark:bg-cyan-950/60 text-blue-600 dark:text-cyan-300 border border-blue-200/60 dark:border-cyan-500/40">
                  24/7
                </span>
              </div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                AI Vip Pro Max
              </span>
            </div>

            <AIIdentity
              avatarOnly
              size="md"
            />
          </button>
        </div>
      )}
    </div>
  );
}
