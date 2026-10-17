import { PatientSelector } from '../features/patient-profiles/PatientSelector';
import { usePatientSelection } from '../features/patient-profiles/usePatientSelection';
import { PatientUpdates, type PatientUpdatesHandle, type SupportRequestState, type Update } from '../features/coordinator/PatientUpdates';
import '../components/ChatMessageInput.css';
import '../components/ChatSendButton.css';
import { AIIdentity } from '../components/AIIdentity';
import { BookingDrawer } from '../features/chat/BookingDrawer';
import { ChatHistoryPanel } from '../features/chat/ChatHistoryPanel';
import { ChatAccessGate } from '../features/chat/ChatAccessGate';
import { GUEST_PROFILE_EVENT, readGuestProfile, saveGuestProfile, type ChatProfile } from '../features/chat/profile';
import { AssistantMessage } from '../features/chat/AssistantMessage';
import { SosButton } from '../features/chat/SosButton';
import { BodyMap } from '../features/chat/bodyMap/BodyMap';
import { BodyMapSheet } from '../features/chat/bodyMap/BodyMapSheet';
import { ConsultationProgress } from '../features/chat/ConsultationProgress';
import { ScheduleGrid } from '../features/chat/ScheduleGrid';
import { Visible } from '../features/uiVisibility/Visible';
import { isUiHidden } from '../features/uiVisibility/store';
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
  MapPin,
  Maximize2,
  Mic,
  Minimize2,
  Minus,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { closeChat, toggleChat, type RootState } from '../app/store';
import { peekQuery, rememberQuery } from '../app/queryCache';
import {
  getConversation,
  type SavedChatTurn,
  sendChat,
  streamChat,
  type BookingIntake,
  type ChatMetadata,
  type ConsultationProgressData,
  type ProgressStepKey,
  fetchTakeoverTicket,
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
  /** Dòng trạng thái khi đang chờ (Đang phân tích triệu chứng…). */
  statusText?: string;
  error?: boolean;
  metadata?: ChatMetadata;
  staff?: boolean;
  elapsedMs?: number | null;
}

const STREAM_STAGE_LABELS: Record<string, string> = {
  preparing: 'Đang tải hồ sơ và lịch sử trò chuyện…',
  'node:route_intent': 'Đang xác định nhu cầu của bạn…',
  'node:analyze': 'Đang phân tích triệu chứng…',
  'node:critic': 'Đang kiểm tra an toàn y khoa…',
  'node:find_doctors': 'Đang tìm bác sĩ và lịch khám phù hợp…',
  'node:info_agent': 'Đang tra cứu thông tin…',
  'node:respond': 'Đang soạn câu trả lời…',
  saving: 'Đang lưu hội thoại…',
};

const DEFAULT_QUICK_REPLIES = [
  'Đau đầu, chóng mặt kéo dài',
  'Tức ngực, khó thở khi gắng sức',
  'Tư vấn khám sức khỏe tổng quát',
  'Đặt lịch khám Bác sĩ chuyên khoa',
];

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  sender: 'bot',
  text: 'Kính chào anh/chị! Em là trợ lý tiếp đón của VCare+.\n\nAnh/chị cứ kể theo cách của mình: khó chịu ở đâu, từ khi nào, nặng hay nhẹ. Nếu khó diễn tả, anh/chị có thể chỉ vào chỗ khó chịu trên hình cơ thể.',
  time: '',
};

// Ảnh chụp hội thoại trong bộ nhớ (theo tài khoản, xem queryCache) để quay lại tab chat thấy ngay tin cũ;
// lịch sử từ server vẫn được tải lại và ghi đè.
const CHAT_SNAPSHOT_TTL_MS = 30 * 60_000;
// Nút backend gửi cho người kể chung chung; trên web mở hình cơ thể thay vì gửi chữ (Zalo vẫn gửi chữ).
const BODY_MAP_TRIGGERS = new Set(['Đau ở một chỗ', 'Pain in one spot']);
// Luồng đã xong (đã chọn cơ sở → bác sĩ → giờ, hoặc chốt đặt lịch), chỉ còn điền liên hệ. Lúc còn đang chọn
// bác sĩ/giờ (TRIAGED_READY_FOR_BOOKING, SLOT_CHOICE_REQUIRED) thì chưa mở phiếu.
const BOOKING_READY_STATUSES = new Set([
  'CONFIRM_BOOKING_CONVERSATIONALLY',
  'BOOKING_CONTACT_REQUIRED',
]);
const EDIT_PREFILL: Partial<Record<ProgressStepKey, string>> = {
  symptom: 'Không phải, ý tôi là ',
  details: 'Em ghi chưa đúng, thực ra ',
};
const chatSnapshotKey = (sessionId: string) => `chat:snapshot:${sessionId}`;
function chatSnapshot(sessionId: string | null): Message[] {
  return (sessionId && peekQuery<Message[]>(chatSnapshotKey(sessionId))) || [WELCOME_MESSAGE];
}

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
  const [messages, setMessages] = useState<Message[]>(() => chatSnapshot(sessionStorage.getItem('p124_chat_session_id')));
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
  const [bodyMapSheetOpen, setBodyMapSheetOpen] = useState(false);
  const [bodyMapPulse, setBodyMapPulse] = useState(false);
  const closeBodyMapSheet = useCallback(() => setBodyMapSheetOpen(false), []);
  // Backend gửi phiếu điền sẵn (required) ở mọi lượt → chỉ tự mở khi luồng đã tới bước đặt lịch (đã định khoa,
  // chọn nơi khám/xem lịch) và mỗi cuộc trò chuyện chỉ tự mở một lần; đóng rồi thì mở lại bằng nút "Phiếu khám".
  const autoOpenedDrawerSession = useRef<string | null>(null);
  const openBookingDrawerWhenReady = (metadata: ChatMetadata) => {
    if (!metadata.booking_intake?.required || metadata.is_emergency) return;
    if (!BOOKING_READY_STATUSES.has(metadata.workflow_status || '')) return;
    if (autoOpenedDrawerSession.current === sessionId) return;
    autoOpenedDrawerSession.current = sessionId;
    setIsBookingDrawerOpen(true);
  };
  const [submittedBooking, setSubmittedBooking] = useState<{ sessionId: string; code: string } | null>(null);

  // Điền sẵn ô nhập (không gửi) để người bệnh tự sửa cho đúng ý rồi mới bấm Gửi.
  const focusInputEnd = () => requestAnimationFrame(() => {
    const input = inputRef.current;
    if (!input) return;
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  });
  const prefillInput = useCallback((text: string) => {
    setInputText(text);
    focusInputEnd();
  }, []);
  // Hình cơ thể: chọn thêm vùng thì nối vào câu đang soạn ("…, kèm theo đau lưng") thay vì ghi đè.
  const appendFromBodyMap = useCallback((text: string) => {
    setInputText((current) => {
      const draft = current.trim().replace(/[.,;\s]+$/, '');
      return draft ? `${draft}, kèm theo ${text.replace(/^Tôi (?:hay )?bị\s*/i, '')}` : text;
    });
    focusInputEnd();
  }, []);

  const openBodyMap = () => {
    if (embedded && window.matchMedia('(min-width: 1280px)').matches) {
      setBodyMapPulse(true);
      window.setTimeout(() => setBodyMapPulse(false), 2800);
    } else {
      setBodyMapSheetOpen(true);
    }
  };

  const handleCoordinatorMessages = useCallback((updates: Update[]) => {
    setMessages((prev) => {
      const coordMsgs = updates.filter((u) => u.sender === 'coordinator');
      if (coordMsgs.length === 0) return prev;

      const newItems: Message[] = [];
      for (const u of coordMsgs) {
        const id = `coord-${u.id}`;
        if (!prev.some((m) => m.id === id || m.id === `takeover-${u.id}`)) {
          newItems.push({
            id,
            sender: 'bot',
            staff: true,
            text: u.body,
            time: new Date(u.created_at).toLocaleTimeString('vi-VN', {
              hour: '2-digit',
              minute: '2-digit',
            }),
          });
        }
      }
      if (newItems.length === 0) return prev;
      return [...prev, ...newItems];
    });
  }, []);

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
    const settled = messages.filter((message) => !message.pending);
    if (settled.length > 1 || (settled.length === 1 && settled[0].id !== WELCOME_MESSAGE.id)) {
      rememberQuery(chatSnapshotKey(sessionId), settled, CHAT_SNAPSHOT_TTL_MS);
    }
  }, [messages, sessionId]);

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
      setMessages(chatSnapshot(sharedSession));
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
    // Tin nhắn điều phối viên của phiên được PatientUpdates nạp qua /coordination/live (lần poll đầu lấy toàn bộ,
    // các lần sau chỉ lấy tin mới) → giữ lại tin đã nhận, không để lịch sử AI tải sau ghi đè mất.
    getConversation(sessionId, 0, controller.signal).then(data => {
      if (controller.signal.aborted) return;
      const archived = savedMessages(data.turns);
      setMessages(current => {
        const staffMessages = current.filter(message => message.staff);
        return archived.length || staffMessages.length ? [...archived, ...staffMessages] : [WELCOME_MESSAGE];
      });
      setHistoryMore(data.has_more); setHistoryOffset(data.turns.length);
    }).catch((error: Error & { status?: number }) => {
      if (controller.signal.aborted) return;
      if (error.status === 404) { setMessages([WELCOME_MESSAGE]); setHistoryMore(false); setHistoryOffset(0); }
      else setHistoryError(error.message || 'Không thể tải lịch sử.');
    }).finally(() => { if (historyRequest.current === controller) setHistoryLoading(false); });
    return () => controller.abort();
  }, [sessionId, ownerKey, authUser?.id, isChatOpen, historyReload]);

  useEffect(() => {
    if (!authUser?.id || !isChatOpen) return undefined;
    let stopped = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    const connect = async () => {
      if (stopped) return;
      const ticket = await fetchTakeoverTicket().catch(() => null);
      if (stopped) return;
      socket = new WebSocket(resolveChatTakeoverWebSocketUrl(sessionId, ticket));
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string;
            message?: { id?: string; content?: string; created_at?: string; author_type?: string };
          };
          const message = payload.message;
          const content = message?.content;
          if (payload.type !== 'takeover.message_created' || !message?.id || typeof content !== 'string' || message.author_type !== 'staff') return;
          // Điều phối viên đã tiếp quản: đồng bộ control để giao diện chuyển sang chế độ nhắn với người.
          supportRef.current?.wake();
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
      socket.onclose = (event) => {
        if (event.code === 1008 || event.code === 1000) return;
        if (!stopped) reconnectTimer = window.setTimeout(connect, 10000);
      };
      socket.onerror = () => socket?.close();
    };

    void connect();
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
    // Chỉ bỏ qua khi có request mới thay thế; nếu bị hủy mà không có request thay thế thì vẫn phải tắt "đang tải",
    // nếu không cờ này kẹt true và khóa toàn bộ nút (xóa, gửi, mở lịch sử) cho tới khi F5.
    finally { if (historyRequest.current === controller) setHistoryLoading(false); }
  };

  const openConversation = (id: string) => {
    if (isSending || historyDeleting || historyLoading) return;
    sessionStorage.setItem('p124_chat_session_id', id); setSessionId(id);
    setHistoryOpen(false); setMessages([WELCOME_MESSAGE]); setHistoryError(''); setInputText('');
    if (id === sessionId) setHistoryReload(value => value + 1);
  };

  // Chẩn đoán tạm thời: in các cờ khóa mỗi khi đổi, để biết cờ nào làm nút xóa/gửi bị "cấm".
  useEffect(() => {
    console.info('[chat-flags]', { isSending, historyLoading, historyDeleting, historyError: Boolean(historyError), chatLocked, sessionId });
  }, [isSending, historyLoading, historyDeleting, historyError, chatLocked, sessionId]);

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

    if (supportState.control === 'human') {
      const stamp = Date.now();
      const userMsgId = `user-${stamp}`;
      setMessages((current) => [
        ...current,
        { id: userMsgId, sender: 'user', text, time: displayTime() },
      ]);
      setInputText('');
      isNearBottomRef.current = true;
      setTimeout(() => {
        scrollToBottom(true);
        ensureChatVisibleInPage();
      }, 40);

      try {
        await supportRef.current?.sendMessage(text);
      } catch {
        setMessages((current) => [
          ...current,
          {
            id: `err-${Date.now()}`,
            sender: 'bot',
            text: 'Không thể gửi tin nhắn cho Bác sĩ điều phối. Vui lòng thử lại.',
            time: displayTime(),
            error: true,
          },
        ]);
      }
      return;
    }

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
        onStatus: (stage) => {
          const label = STREAM_STAGE_LABELS[stage];
          if (label) updateBot(botId, { statusText: label });
        },
        onToken: (token) => {
          streamedText += token;
          updateBot(botId, { text: streamedText, pending: false });
          if (isNearBottomRef.current) {
            scrollToBottom(false);
          }
        },
        onMetadata: (metadata) => {
          receivedMetadata = true;
          // Đo phía trình duyệt (gồm mạng/proxy) = thời gian người dùng thực sự chờ; số của server nằm trong metadata.
          const currentElapsed = Date.now() - sendStartTime;
          recordedElapsedMs = currentElapsed;
          updateBot(botId, {
            metadata: {
              ...metadata,
              elapsed_ms: currentElapsed,
            },
            elapsedMs: currentElapsed,
          });
          openBookingDrawerWhenReady(metadata);
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
        openBookingDrawerWhenReady(result);
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
      // Lượt này có thể đã đưa ca lên bàn điều phối → bật lại theo dõi tin nhắn của điều phối viên (kể cả khách).
      if (completed) supportRef.current?.wake();
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
    setSubmittedBooking({ sessionId, code: requestCode });
  }, [sessionId]);

  // Tiến trình lấy từ lượt trả lời gần nhất; phiếu gửi qua drawer thì đánh dấu bước "Đặt lịch" xong ngay.
  const latestProgress = (() => {
    const progress = [...messages].reverse().find((message) => message.sender === 'bot' && message.metadata?.progress)?.metadata?.progress;
    if (!progress || submittedBooking?.sessionId !== sessionId || progress.emergency) return progress;
    const steps: ConsultationProgressData['steps'] = progress.steps.map((step) =>
      step.key === 'booking' ? { ...step, status: 'done', summary: `Đã gửi yêu cầu · mã ${submittedBooking.code}` } : step);
    return { ...progress, steps, current_step: steps.length };
  })();

  const handleQuickReply = (reply: string) => {
    // Hình cơ thể bị admin ẩn → gửi chữ, bot hỏi vùng đau (giống Zalo).
    if (BODY_MAP_TRIGGERS.has(reply) && !isUiHidden('consult.body_map')) { openBodyMap(); return; }
    void sendMessage(reply);
    ensureChatVisibleInPage();
  };

  const latestBotMessageId = [...messages].reverse().find((message) => message.sender === 'bot' && !message.staff)?.id;
  const latestQuickReplies =
    [...messages]
      .reverse()
      .find((message) => message.sender === 'bot' && message.metadata?.quick_replies?.length)
      ?.metadata?.quick_replies || DEFAULT_QUICK_REPLIES;
  const showStarter = embedded && messages.length === 1 && messages[0].id === 'welcome' && !isSending && supportState.control !== 'human';
  const supportLabel = supportState.control === 'human'
    ? 'Đang kết nối bác sĩ'
    : supportState.requested ? 'Đã gửi yêu cầu' : 'Yêu cầu hỗ trợ';

  return (
    <div
      className={
        embedded
          ? 'flex h-full min-h-0 w-full flex-col'
          : 'fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[9999] flex flex-col items-end pointer-events-none'
      }
    >
      {/* ─── CHAT WINDOW MODAL / EMBEDDED CONTAINER ─── */}
      {isChatOpen && (
        <section
          className={`flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800/90 bg-white/95 dark:bg-app-page/95 backdrop-blur-2xl transition-all duration-300 pointer-events-auto ${
            embedded
              ? 'h-full min-h-0 w-full shadow-lg dark:shadow-2xl max-sm:rounded-none max-sm:border-0 max-sm:shadow-none'
              : isExpanded
              ? 'h-[88vh] w-[min(48rem,calc(100vw-2rem))] shadow-2xl shadow-blue-950/25 dark:shadow-cyan-950/40 ring-1 ring-blue-500/10 dark:ring-cyan-500/20'
              : 'h-[min(744px,calc(100dvh-2rem))] w-[min(32.5rem,calc(100vw-1.5rem))] shadow-2xl shadow-blue-950/20 dark:shadow-black/60 ring-1 ring-blue-500/10 dark:ring-cyan-500/20'
          }`}
          aria-label="Trợ lý tiếp đón VCare+"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#d5e8de] dark:border-white/10 bg-gradient-to-r from-[#edf7f1] via-[#f6fcf9] to-[#edf7f1] dark:from-app-page dark:via-app-surface dark:to-app-page px-4 py-3.5 text-[#295c49] dark:text-white">
            <div className="flex items-center gap-3">
              <div className="flex min-w-0 flex-col gap-2">
                <AIIdentity />
              </div>
            </div>

            {/* Action buttons */}
            <div className={embedded ? 'chat-acts' : 'flex items-center gap-1 text-[#527565] dark:text-slate-300'}>
              <Visible id="consult.support_button" inline>
              <button
                type="button"
                disabled={chatLocked || supportState.busy || supportState.requested || supportState.control === 'human'}
                aria-label={supportLabel}
                title={supportLabel}
                onClick={() => supportRef.current?.requestHuman()}
                className={embedded ? 'chat-act chat-act--support' : 'inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-medium hover:bg-emerald-100 dark:hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50'}
              >
                <Headset className={embedded ? 'chat-act__icon' : 'h-4 w-4 shrink-0'} />
                <span className={embedded ? 'chat-act__label' : 'sr-only'}>{supportLabel}</span>
              </button>
              </Visible>
              {authUser && <Visible id="consult.history_button" inline><button type="button" disabled={isSending || historyDeleting || historyLoading} aria-label="Lịch sử trò chuyện" title="Lịch sử trò chuyện" onClick={() => setHistoryOpen(value => !value)} className={embedded ? 'chat-act' : 'rounded-lg p-2 hover:bg-emerald-100 dark:hover:bg-white/10 disabled:opacity-50'}><History className={embedded ? 'chat-act__icon' : 'h-4 w-4'} />{embedded && <span className="chat-act__label">Lịch sử</span>}</button></Visible>}
              <Visible id="consult.booking_button" inline>
              <button
                type="button"
                onClick={() => setIsBookingDrawerOpen((prev) => !prev)}
                className={embedded ? 'chat-act' : 'flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-[#28785c] dark:text-cyan-200 hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white transition-colors cursor-pointer'}
                aria-label="Phiếu khám"
                title="Mở phiếu hẹn khám bác sĩ chuyên khoa"
              >
                <ClipboardList className={embedded ? 'chat-act__icon' : 'h-3.5 w-3.5 text-cyan-400'} />
                <span className={embedded ? 'chat-act__label' : 'hidden sm:inline'}>Phiếu khám</span>
              </button>
              </Visible>
              <Visible id="consult.new_chat_button" inline>
              <button
                type="button"
                onClick={resetConversation}
                className={embedded ? 'chat-act' : 'rounded-lg p-1.5 transition-colors hover:bg-emerald-100 dark:hover:bg-white/10 hover:text-emerald-800 dark:hover:text-white cursor-pointer'}
                aria-label="Cuộc trò chuyện mới"
                title="Tạo cuộc hội chẩn mới"
              >
                <RotateCcw className={embedded ? 'chat-act__icon' : 'h-4 w-4'} />
                {embedded && <span className="chat-act__label">Cuộc mới</span>}
              </button>
              </Visible>
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
          <div inert={chatLocked} aria-hidden={chatLocked || undefined} className={`flex min-h-0 flex-1 ${chatLocked ? 'pointer-events-none select-none blur-sm' : ''}`}>
          {/* Hình cơ thể: cột trái trên màn rộng; màn nhỏ mở bằng nút 📍 cạnh ô nhập (BodyMapSheet). */}
          {embedded && (
            <Visible id="consult.body_map">
            <aside className={`hidden w-[270px] shrink-0 overflow-y-auto border-r border-slate-200/80 dark:border-slate-800/80 px-4 pt-4 pb-24 xl:block ${bodyMapPulse ? 'body-map--pulse' : ''}`} aria-label="Hình cơ thể">
              <BodyMap onPick={appendFromBodyMap} disabled={supportState.control === 'human'} />
            </aside>
            </Visible>
          )}
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {/* Message List */}
          <Visible id="consult.patient_selector"><PatientSelector selection={patientSelection} disabled={isSending || historyLoading} /></Visible>
          {latestProgress && supportState.control !== 'human' && (
            <Visible id="consult.progress">
              <ConsultationProgress progress={latestProgress} disabled={isSending}
                onEdit={(step) => prefillInput(EDIT_PREFILL[step] ?? '')} />
            </Visible>
          )}
          <Visible id="chat.coordinator_status">
          {supportState.control === 'human' && (
            <div className="flex items-center justify-between border-b border-emerald-500/20 bg-emerald-50/90 dark:bg-emerald-950/40 px-3.5 py-1.5 text-xs text-emerald-800 dark:text-emerald-200">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                </span>
                <span className="font-semibold text-[11px]">Bác sĩ điều phối đang trực tiếp hỗ trợ</span>
              </div>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/60 px-2 py-0.5 text-[9px] font-bold text-emerald-700 dark:text-emerald-300">
                Trực tuyến
              </span>
            </div>
          )}
          {supportState.requested && supportState.control !== 'human' && (
            <div className="flex items-center gap-2 border-b border-amber-500/20 bg-amber-50/90 dark:bg-amber-950/40 px-3.5 py-1.5 text-xs text-amber-800 dark:text-amber-200">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500"></span>
              </span>
              <span className="font-medium text-[11px]">Đã gửi yêu cầu hỗ trợ. Đang chờ Bác sĩ điều phối tiếp nhận phiên…</span>
            </div>
          )}
          </Visible>
          {authUser && historyOpen && <ChatHistoryPanel patientProfileId={patientSelection.profileId || undefined} key={authUser.id + patientSelection.profileId} activeSessionId={sessionId} onSelect={openConversation} busy={isSending || historyLoading} onDeletingChange={setHistoryDeleting} onDeleted={id => { if (id === sessionId) { historyRequest.current?.abort(); setHistoryLoading(false); setHistoryError(''); setHistoryMore(false); setHistoryOffset(0); resetConversation(); } }} />}
          {historyError && <p role="alert" className="px-4 py-2 text-xs text-red-600">{historyError} <button type="button" onClick={() => setHistoryReload(value => value + 1)} className="underline">Thử tải lại</button></p>}
          {historyLoading && <p className="px-4 py-2 text-xs text-app-secondary">Đang tải cuộc trò chuyện…</p>}
          {historyMore && <button disabled={historyLoading || isSending} type="button" onClick={loadOlderMessages} className="px-4 py-2 text-xs text-blue-600">Tải tin nhắn cũ hơn</button>}
          <div
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
            className={`${embedded ? 'chat-stage ' : ''}flex-1 space-y-4 overflow-y-auto overscroll-contain bg-[#f6fcf9] dark:bg-app-deep/90 p-3 text-xs transition-colors scroll-smooth sm:p-4 ${embedded ? 'sm:px-6 lg:py-6 [&>*]:mx-auto [&>*]:w-full [&>*]:max-w-[820px]' : ''}`}
            aria-live="polite"
          >
            {messages.map((message) => {
              const candidates = message.metadata?.candidate_specialties || [];
              // Lưới lịch chỉ bấm được ở tin nhắn bot mới nhất (lịch cũ có thể đã hết chỗ).
              const scheduleGrid = message.id === latestBotMessageId && supportState.control !== 'human' ? message.metadata?.schedule_grid : null;
              const isUser = message.sender === 'user';

              return (
                <div key={message.id} className={isUser ? 'flex justify-end' : 'flex items-start gap-2.5'}>
                  {!isUser && (
                    <span className="mt-1 shrink-0">
                      {message.staff ? (
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-[#176a52] dark:bg-emerald-900/60 dark:text-emerald-300 ring-2 ring-emerald-500/20 font-bold text-[10px]">
                          BS
                        </div>
                      ) : (
                        <AIIdentity avatarOnly />
                      )}
                    </span>
                  )}

                  <div
                    className={`${
                      isUser
                        ? 'max-w-[85%] rounded-2xl rounded-tr-xs bg-gradient-to-r from-[#37856a] to-[#296c55] dark:from-blue-600 dark:to-blue-700 px-4 py-3 text-white shadow-md shadow-emerald-900/10 dark:shadow-blue-600/20'
                        : `max-w-[90%] rounded-2xl rounded-tl-xs border bg-white dark:bg-app-surface p-4 shadow-sm text-slate-800 dark:text-slate-100 ${
                            message.error
                              ? 'border-red-200 dark:border-red-900/50'
                              : 'border-slate-200/90 dark:border-slate-800/90'
                          }`
                    }`}
                  >
                    {/* Doctor Supervision Stamp on Bot Messages */}
                    {!isUser && (
                      <div className="mb-2 flex items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-1.5">
                        <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                          {message.staff ? (
                            <>
                              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                              <span>Bác sĩ điều phối</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                              <span>Trợ lý AI VCare+</span>
                            </>
                          )}
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                          {message.time || displayTime()}
                        </span>
                      </div>
                    )}

                    {/* ATS Triage Badge */}
                    {!isUser && <Visible id="chat.emergency_banner"><AtsBadge metadata={message.metadata} /></Visible>}

                    {/* Content */}
                    {message.pending && !message.text ? (
                      <div className="flex items-center gap-2.5 py-1 text-slate-500 dark:text-slate-400 font-medium">
                        <LoaderCircle className="h-4 w-4 animate-spin text-blue-500 dark:text-cyan-400" />
                        <span>{message.statusText || 'Đang chờ phản hồi từ trợ lý…'}</span>
                      </div>
                    ) : (
                      <div className={`${isUser ? 'whitespace-pre-wrap' : ''} break-words leading-relaxed ${embedded ? 'text-[14px] sm:text-[15px]' : 'text-xs sm:text-[13px]'}`}>
                        {isUser ? message.text : <AssistantMessage text={message.text} />}
                      </div>
                    )}

                    {/* Candidate Specialties Card */}
                    {candidates.length > 0 && (
                      <div className="mt-3 rounded-xl border border-[#cde5d7] dark:border-blue-900/60 bg-[#edf7f1] dark:bg-app-surface p-3 text-[11px] text-[#295c49] dark:text-cyan-200">
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

                    {scheduleGrid && (
                      <Visible id="consult.schedule_grid">
                        <ScheduleGrid grid={scheduleGrid} disabled={isSending || historyLoading} onPick={handleQuickReply} />
                      </Visible>
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
            {showStarter && (
              <Visible id="consult.starter">
              <div className="chat-start">
                <p className="chat-start__title">Bạn muốn bắt đầu từ đâu?</p>
                <div className="chat-start__grid">
                  {latestQuickReplies.slice(0, 4).map((reply, index) => (
                    <button
                      key={reply}
                      type="button"
                      disabled={isSending || historyDeleting || historyLoading || Boolean(historyError)}
                      onClick={() => { void sendMessage(reply); ensureChatVisibleInPage(); }}
                      className="chat-start__card"
                    >
                      <span className="chat-start__num" aria-hidden="true">{index + 1}</span>
                      <span>{reply}</span>
                    </button>
                  ))}
                </div>
                <p className="chat-start__hint">Mỗi lượt AI chỉ hỏi một câu ngắn. Có dấu hiệu nguy hiểm, hãy gọi 115 ngay.</p>
              </div>
              </Visible>
            )}
            <PatientUpdates
              key={ownerKey + sessionId}
              ref={supportRef}
              sessionId={sessionId}
              owner={ownerKey}
              mode="embedded"
              showRequestButton={false}
              onSupportStateChange={setSupportState}
              onCoordinatorMessages={handleCoordinatorMessages}
            />
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Reply Suggestions */}
          {latestQuickReplies.length > 0 && supportState.control !== 'human' && !showStarter && (
            <Visible id="consult.quick_replies">
            <div className={`flex gap-2 overflow-x-auto border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-app-page/95 px-3.5 py-2.5 no-scrollbar ${embedded ? '[&>*:first-child]:ml-auto [&>*:last-child]:mr-auto' : ''}`}>
              {latestQuickReplies.slice(0, 4).map((reply) => (
                <button
                  key={reply}
                  type="button"
                  disabled={isSending || historyDeleting || historyLoading || Boolean(historyError)}
                  onClick={() => handleQuickReply(reply)}
                  className="whitespace-nowrap rounded-full border border-[#cde5d7] dark:border-slate-700/80 bg-[#f6fcf9] dark:bg-slate-800/90 px-3 py-2 text-xs sm:py-1.5 sm:text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-emerald-500 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:border-cyan-400 dark:hover:bg-slate-700 dark:hover:text-cyan-300 disabled:opacity-50 transition-all shadow-xs cursor-pointer active:scale-95 shrink-0"
                >
                  {reply}
                </button>
              ))}
            </div>
            </Visible>
          )}

          {/* Input & Action Bar */}
          <div className="border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-app-page/95 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-md">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void sendMessage(inputText);
                ensureChatVisibleInPage();
              }}
              className={`flex items-center gap-2 ${embedded ? 'chat-composer mx-auto max-w-[820px]' : ''}`}
            >
              <div className="chat-message-input-container">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  disabled={isSending || historyDeleting || historyLoading || Boolean(historyError)}
                  onFocus={ensureChatVisibleInPage}
                  onChange={(event) => setInputText(event.target.value)}
                  placeholder={
                    supportState.control === 'human'
                      ? 'Nhắn tin cho Bác sĩ điều phối…'
                      : 'Mô tả triệu chứng, vị trí và thời gian bắt đầu…'
                  }
                  aria-label="Nội dung tin nhắn"
                  className="chat-message-input"
                />
              </div>
                <Visible id="consult.body_map_button" inline>
                <button
                  type="button"
                  disabled={supportState.control === 'human'}
                  onClick={() => setBodyMapSheetOpen(true)}
                  className={`chat-message-input-map ${embedded ? 'chat-message-input-map--embedded' : ''}`}
                  aria-label="Chỉ chỗ khó chịu trên hình cơ thể"
                  title="Chỉ chỗ khó chịu trên hình cơ thể"
                >
                  <MapPin className="h-4 w-4" />
                </button>
                </Visible>
                <Visible id="consult.voice_button" inline>
                <button
                  type="button"
                  disabled
                  className="chat-message-input-mic"
                    aria-label="Nhập bằng giọng nói (sắp ra mắt)"
                  title="Tính năng nhập giọng nói sắp ra mắt"
                >
                  <Mic className="h-4 w-4" />
                </button>
                </Visible>

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

            <Visible id="chat.disclaimer">
            <p className="mt-1 text-center text-[10px] leading-snug text-slate-500 dark:text-slate-400 sm:mt-2">
              VCare+ hỗ trợ tư vấn sơ bộ, không chẩn đoán hay kê đơn. Với triệu chứng nguy cấp, xin vui lòng gọi{' '}
              <SosButton variant="link" />{' '}
              ngay.
            </p>
            </Visible>
          </div>
          </div>
          </div>
          {chatLocked && <ChatAccessGate onGuest={saveGuestProfile} />}
          </div>
        </section>
      )}

      {isChatOpen && !chatLocked && (
        <BodyMapSheet open={bodyMapSheetOpen} onClose={closeBodyMapSheet} onPick={appendFromBodyMap} />
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
            className="group relative flex items-center gap-3 rounded-full border border-blue-200/90 dark:border-cyan-500/35 bg-white/95 dark:bg-app-page/95 backdrop-blur-xl py-2.5 pl-4 pr-3 shadow-xl dark:shadow-2xl shadow-blue-900/10 dark:shadow-cyan-500/15 hover:shadow-2xl hover:shadow-blue-500/30 dark:hover:shadow-cyan-400/25 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer ring-1 ring-blue-500/10 dark:ring-cyan-400/20"
            aria-label="Mở trợ lý VCare+"
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
                  VCare+
                </span>
              </div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                Trợ lý tiếp đón y tế
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
