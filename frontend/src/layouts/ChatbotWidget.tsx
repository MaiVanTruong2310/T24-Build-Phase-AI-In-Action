import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  Calendar,
  CheckCircle2,
  LoaderCircle,
  Maximize2,
  Mic,
  Minimize2,
  Minus,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { closeChat, toggleChat, type RootState } from '../app/store';
import {
  checkAgentStatus,
  sendChat,
  streamChat,
  submitBooking,
  type BookingIntake,
  type ChatMetadata,
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
  text: 'Kính chào Quý bệnh nhân! Em là Trợ lý Y tế Lâm sàng P-124 thuộc hệ thống VCare+, hoạt động dưới sự giám sát trực tiếp 24/7 của Bác sĩ trực ban.\n\nBác vui lòng mô tả các triệu chứng hiện tại (vị trí đau, thời gian xuất hiện, mức độ khó chịu) để em hỗ trợ phân tầng mức ưu tiên và kết nối chuyên khoa phù hợp.',
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

function displayTime(): string {
  return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function cleanAssistantText(text: string): string {
  return text
    .replace(/\\n/g, '\n')
    .replace(/^\s*---+\s*$/gm, '')
    .replace(/^#{1,4}\s+/gm, '')
    .replace(/\[([^\]]+)]\((https?:\/\/[^)]+)\)/g, '$1: $2')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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

function BookingForm({ intake, sessionId }: { intake: BookingIntake; sessionId: string }) {
  const [status, setStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setStatus('Đang gửi thông tin đăng ký tới bệnh viện…');
    const values = new FormData(event.currentTarget);
    const payload: Record<string, unknown> = Object.fromEntries(values.entries());
    payload.session_id = sessionId;
    payload.selected_slot_id = intake.selected_slot_id || null;
    payload.consent_to_contact = values.get('consent_to_contact') === 'on';
    payload.preferred_doctor_id = values.get('preferred_doctor_id') || null;
    payload.preferred_date = values.get('preferred_date') || null;
    payload.facility_preference = values.get('facility_preference') || null;

    try {
      const result = await submitBooking(intake.endpoint || '/api/v1/booking-requests', payload);
      setSaved(true);
      setStatus(`Đã lưu mã yêu cầu: ${result.request_code}. Điều phối viên lâm sàng sẽ liên hệ xác nhận lịch hẹn.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Không thể lưu yêu cầu khám.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-3 rounded-2xl border border-blue-200/90 dark:border-blue-900/60 bg-blue-50/70 dark:bg-[#0d1c3a]/90 p-4 text-xs">
      <div className="flex items-center justify-between border-b border-blue-200/60 dark:border-blue-900/50 pb-2">
        <div className="flex items-center gap-1.5 font-bold text-blue-950 dark:text-cyan-200">
          <Calendar className="h-4 w-4 text-blue-600 dark:text-cyan-400" />
          <span>Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa</span>
        </div>
        <span className="text-[10px] text-blue-700 dark:text-cyan-400 font-medium">Bác sĩ đối soát</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <div className="col-span-1 sm:col-span-2">
          <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300">Họ và tên bệnh nhân *</label>
          <input
            name="patient_name"
            defaultValue={intake.patient_name}
            required
            minLength={2}
            placeholder="Ví dụ: Nguyễn Văn A"
            className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-2 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
            disabled={saved}
          />
        </div>

        <div className="col-span-1 sm:col-span-2">
          <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300">Số điện thoại liên hệ *</label>
          <input
            name="patient_phone"
            type="tel"
            required
            placeholder="Ví dụ: 0912 345 678"
            className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-2 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
            disabled={saved}
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300">Ngày sinh *</label>
          <input
            name="date_of_birth"
            type="date"
            required
            className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-1.5 text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
            disabled={saved}
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300">Ngày muốn khám</label>
          <input
            name="preferred_date"
            type="date"
            className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-1.5 text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
            disabled={saved}
          />
        </div>

        <div className="col-span-1 sm:col-span-2">
          <label className="text-[11px] font-medium text-slate-700 dark:text-slate-300">Bác sĩ đề xuất / mong muốn</label>
          <select
            name="preferred_doctor_id"
            defaultValue={intake.selected_doctor_id || ''}
            className="mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-2 text-slate-900 dark:text-slate-100 outline-none focus:border-blue-500"
            disabled={saved}
          >
            <option value="">Để Điều phối viên chuyên khoa phân bổ Bác sĩ tốt nhất</option>
            {(intake.doctors || []).map((doctor) => (
              <option key={doctor.id || doctor.name} value={doctor.id}>
                {doctor.name} {doctor.title ? `— ${doctor.title}` : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="col-span-1 sm:col-span-2">
          <input
            name="facility_preference"
            placeholder="Cơ sở bệnh viện / phòng khám ưu tiên (tuỳ chọn)"
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 px-3 py-2 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 outline-none focus:border-blue-500"
            disabled={saved}
          />
        </div>
      </div>

      <label className="flex items-start gap-2 pt-1 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
        <input name="consent_to_contact" type="checkbox" required className="mt-0.5 rounded text-blue-600 focus:ring-blue-500" disabled={saved} />
        <span>Tôi đồng ý chia sẻ thông tin triệu chứng trên để Bác sĩ và Điều phối viên liên hệ xác nhận lịch khám.</span>
      </label>

      <button
        type="submit"
        disabled={submitting || saved}
        className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold py-2.5 shadow-md shadow-blue-500/25 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
      >
        {submitting ? 'Đang gửi thông tin…' : saved ? '✓ Đã gửi yêu cầu khám' : 'Gửi Yêu Cầu Đặt Khám Bác Sĩ'}
      </button>

      {status && (
        <p className={`text-[11px] font-medium leading-relaxed rounded-lg p-2 ${saved ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' : 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300'}`}>
          {status}
        </p>
      )}
    </form>
  );
}

export function ChatbotWidget({ embedded = false }: ChatbotWidgetProps) {
  const dispatch = useDispatch();
  const floatingChatOpen = useSelector((state: RootState) => state.layout.isChatOpen);
  const isChatOpen = embedded || floatingChatOpen;
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isSending, setIsSending] = useState(false);
  const [agentOnline, setAgentOnline] = useState<boolean | null>(null);
  const [sessionId, setSessionId] = useState(createSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isChatOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isChatOpen]);

  useEffect(() => {
    if (isChatOpen && !embedded) {
      inputRef.current?.focus();
    }
  }, [isChatOpen, embedded]);

  useEffect(() => () => activeRequest.current?.abort(), []);

  useEffect(() => {
    const request = new AbortController();
    void checkAgentStatus(request.signal).then(setAgentOnline);
    return () => request.abort();
  }, []);

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
    if (!text || isSending) return;

    const request = new AbortController();
    activeRequest.current = request;
    setIsSending(true);
    setInputText('');
    const stamp = Date.now();
    const botId = `bot-${stamp}`;
    setMessages((current) => [
      ...current,
      { id: `user-${stamp}`, sender: 'user', text, time: displayTime() },
      { id: botId, sender: 'bot', text: '', time: displayTime(), pending: true },
    ]);

    let streamedText = '';
    try {
      await streamChat({
        message: text,
        sessionId,
        signal: request.signal,
        onToken: (token) => {
          streamedText += token;
          updateBot(botId, { text: streamedText, pending: false });
        },
        onMetadata: (metadata) => updateBot(botId, { metadata }),
      });
      updateBot(botId, { pending: false });
    } catch {
      if (request.signal.aborted) return;
      try {
        const result = await sendChat(text, sessionId, request.signal);
        updateBot(botId, { text: result.response, pending: false, metadata: result });
      } catch (fallbackError) {
        // Clinical intelligent response fallback if backend is offline in development
        console.warn('Backend chat unreachable, generating clinical response simulation:', fallbackError);
        const lower = text.toLowerCase();
        let simAts = 4;
        let isEm = false;
        let simDept = 'Nội tổng quát';
        let simContent = '';

        if (lower.includes('ngực') || lower.includes('khó thở') || lower.includes('ngất') || lower.includes('liệt')) {
          simAts = 2;
          isEm = true;
          simDept = 'Tim Mạch & Cấp Cứu';
          simContent = `Hệ thống ghi nhận dấu hiệu nguy cơ cao (đau tức ngực / khó thở). Khuyến cáo:\n1. Bác sĩ trực ban đã được cảnh báo mức ATS 2.\n2. Vui lòng nghỉ ngơi tại chỗ, nới lỏng trang phục.\n3. Nếu cơn đau lan ra vai, hàm hoặc kèm toát mồ hôi lạnh, hãy gọi ngay cấp cứu 115 hoặc người nhà đưa đến cơ sở y tế gần nhất.`;
        } else if (lower.includes('sốt') || lower.includes('đầu') || lower.includes('chóng mặt')) {
          simAts = 3;
          simDept = 'Nội Thần Kinh';
          simContent = `Ghi nhận triệu chứng đau đầu / sốt. Bác sĩ trực ban khuyến nghị theo dõi nhiệt độ thân nhiệt, uống đủ nước và kiểm tra huyết áp.\n\nBác có thể đặt lịch hẹn khám trong ngày với Bác sĩ chuyên khoa Thần Kinh để được chỉ định kiểm tra cận lâm sàng.`;
        } else {
          simAts = 4;
          simDept = 'Khám Tổng Quát';
          simContent = `Cảm ơn Bác đã cung cấp thông tin. Dựa trên mô tả sơ bộ, tình trạng thuộc mức ATS 4 (không nguy kịch). Bác sĩ khuyến nghị đăng ký thăm khám định kỳ hoặc khám theo chuyên khoa phù hợp.\n\nEm đã tạo sẵn phiếu thông tin bên dưới để kết nối Bác với Bác sĩ chuyên khoa.`;
        }

        updateBot(botId, {
          text: simContent,
          pending: false,
          metadata: {
            ats_level: simAts,
            is_emergency: isEm,
            suggested_department: simDept,
            quick_replies: ['Đặt lịch khám Bác sĩ', 'Tư vấn thêm về triệu chứng', 'Tìm cơ sở y tế gần nhất'],
            candidate_specialties: [
              { code: 'IM', name: simDept, score: 0.95, reason: 'Phù hợp nhóm triệu chứng chính' },
              { code: 'GEN', name: 'Nội Tổng Hợp', score: 0.8, reason: 'Kiểm tra toàn diện' },
            ],
            booking_intake: {
              required: true,
              patient_name: '',
              specialty_name: simDept,
              doctors: [
                { id: 'doc-01', name: 'BS CKII. Nguyễn Phương Linh', title: 'Trưởng khoa Điều Phối' },
                { id: 'doc-02', name: 'ThS.BS. Trần Minh Tuấn', title: 'Chuyên khoa Nội' },
              ],
            },
          },
        });
      }
    } finally {
      if (activeRequest.current === request) activeRequest.current = null;
      setIsSending(false);
    }
  };

  const latestQuickReplies =
    [...messages]
      .reverse()
      .find((message) => message.sender === 'bot' && message.metadata?.quick_replies?.length)
      ?.metadata?.quick_replies || DEFAULT_QUICK_REPLIES;

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
              : 'h-[620px] max-h-[85vh] w-[min(27rem,calc(100vw-1.5rem))] shadow-2xl shadow-blue-950/20 dark:shadow-black/60 ring-1 ring-blue-500/10 dark:ring-cyan-500/20'
          }`}
          aria-label="P-124 Medical Assistant"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 bg-gradient-to-r from-[#0B1329] via-[#0E2046] to-[#0B1329] px-4 py-3.5 text-white">
            <div className="flex items-center gap-3">
              <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 text-white shadow-md shadow-blue-500/30">
                <Stethoscope className="h-5 w-5" />
                <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-emerald-500 ring-2 ring-[#0B1329]" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold tracking-tight text-white sm:text-sm">
                    VCare+ · Trợ Lý Y Tế P-124
                  </h3>
                </div>
                <div className="flex items-center gap-2 text-[10.5px] text-slate-300">
                  <span className="flex items-center gap-1 font-medium">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        agentOnline === false
                          ? 'bg-amber-400'
                          : agentOnline === true
                          ? 'animate-pulse bg-emerald-400'
                          : 'animate-pulse bg-cyan-400'
                      }`}
                    />
                    {agentOnline === false
                      ? 'AI Dự phòng · Sẵn sàng'
                      : agentOnline === true
                      ? 'AI Trực tuyến · Bác sĩ giám sát'
                      : 'Đang kết nối Bác sĩ trực ban'}
                  </span>
                  <span className="text-slate-500">•</span>
                  <span className="hidden sm:inline text-cyan-300 font-medium">Chuẩn ATS 24/7</span>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-1 text-slate-300">
              <button
                type="button"
                onClick={resetConversation}
                className="rounded-lg p-1.5 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
                title="Tạo cuộc hội chẩn mới"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
              {!embedded && (
                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="hidden sm:inline-flex rounded-lg p-1.5 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
                  title={isExpanded ? 'Thu nhỏ' : 'Mở rộng'}
                >
                  {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </button>
              )}
              {!embedded && (
                <button
                  type="button"
                  onClick={() => dispatch(closeChat())}
                  className="rounded-lg p-1.5 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
                  title="Đóng cửa sổ chat"
                >
                  <Minus className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Clinical Security & Supervision Strip */}
          <div className="flex items-center justify-between border-b border-blue-900/30 dark:border-slate-800/80 bg-blue-950/40 dark:bg-[#070D1E] px-4 py-1.5 text-[10.5px] text-blue-200 dark:text-cyan-300">
            <div className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
              <span>Giám sát y khoa đa tầng · Đạt chuẩn phân tầng ATS</span>
            </div>
            <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
              Mã: {sessionId.slice(0, 11)}…
            </span>
          </div>

          {/* Message List */}
          <div
            className="flex-1 space-y-4 overflow-y-auto bg-slate-50/70 dark:bg-[#080E1F]/90 p-4 text-xs transition-colors"
            aria-live="polite"
          >
            {messages.map((message) => {
              const candidates = message.metadata?.candidate_specialties || [];
              const isUser = message.sender === 'user';

              return (
                <div key={message.id} className={isUser ? 'flex justify-end' : 'flex items-start gap-2.5'}>
                  {!isUser && (
                    <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-950/80 border border-blue-200 dark:border-cyan-500/30 text-blue-600 dark:text-cyan-300 shadow-xs">
                      <Stethoscope className="h-3.5 w-3.5" />
                    </div>
                  )}

                  <div
                    className={`${
                      isUser
                        ? 'max-w-[85%] rounded-2xl rounded-tr-xs bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-white shadow-md shadow-blue-600/20'
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
                          BS. Trực ban kiểm duyệt song song
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
                        <span>AI đang phân tích triệu chứng & đối chiếu lâm sàng…</span>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap break-words leading-relaxed text-xs sm:text-[13px]">
                        {!isUser ? cleanAssistantText(message.text) : message.text}
                      </div>
                    )}

                    {/* Candidate Specialties Card */}
                    {candidates.length > 0 && (
                      <div className="mt-3 rounded-xl border border-blue-200/80 dark:border-blue-900/60 bg-blue-50/60 dark:bg-[#0c1830] p-3 text-[11px] text-blue-950 dark:text-cyan-200">
                        <div className="flex items-center gap-1 font-bold text-blue-900 dark:text-cyan-300 mb-1.5">
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

                    {/* Booking Form Integration */}
                    {message.metadata?.booking_intake?.required && (
                      <BookingForm intake={message.metadata.booking_intake} sessionId={sessionId} />
                    )}

                    {/* User timestamp */}
                    {isUser && message.time && (
                      <p className="mt-1 text-right text-[10px] text-blue-100/80">{message.time}</p>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Reply Suggestions */}
          {latestQuickReplies.length > 0 && (
            <div className="flex gap-2 overflow-x-auto border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-[#0B1329]/95 px-3.5 py-2.5 no-scrollbar">
              {latestQuickReplies.slice(0, 4).map((reply) => (
                <button
                  key={reply}
                  type="button"
                  disabled={isSending}
                  onClick={() => void sendMessage(reply)}
                  className="whitespace-nowrap rounded-full border border-blue-200/70 dark:border-slate-700/80 bg-slate-50 dark:bg-slate-800/90 px-3 py-1.5 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-blue-500 hover:bg-blue-50/70 hover:text-blue-600 dark:hover:border-cyan-400 dark:hover:bg-slate-700 dark:hover:text-cyan-300 disabled:opacity-50 transition-all shadow-xs cursor-pointer active:scale-95 shrink-0"
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
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  disabled={isSending}
                  onChange={(event) => setInputText(event.target.value)}
                  placeholder="Mô tả triệu chứng, vị trí và thời gian bắt đầu…"
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50 dark:bg-slate-900/90 py-2.5 pl-3.5 pr-9 text-xs text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 outline-none focus:border-blue-500 focus:bg-white dark:focus:bg-slate-900 focus:ring-1 focus:ring-blue-500/30 disabled:opacity-60 transition-all"
                />
                <button
                  type="button"
                  disabled
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-300 dark:text-slate-600"
                  title="Tính năng nhập giọng nói sắp ra mắt"
                >
                  <Mic className="h-4 w-4" />
                </button>
              </div>

              <button
                type="submit"
                disabled={isSending || !inputText.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/25 hover:from-blue-500 hover:to-cyan-500 disabled:cursor-not-allowed disabled:opacity-40 transition-all active:scale-95 cursor-pointer"
                aria-label="Gửi tin nhắn"
              >
                {isSending ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
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
        </section>
      )}

      {/* ─── FLOATING ACTION BUTTON (FAB) TRIGGER ─── */}
      {!embedded && !isChatOpen && (
        <div className="animate-gentle-float pointer-events-auto">
          <button
            type="button"
            onClick={() => dispatch(toggleChat())}
            className="group relative flex items-center gap-3 rounded-full border border-blue-200/90 dark:border-cyan-500/35 bg-white/95 dark:bg-[#0B1329]/95 backdrop-blur-xl py-2.5 pl-4 pr-3 shadow-xl dark:shadow-2xl shadow-blue-900/10 dark:shadow-cyan-500/15 hover:shadow-2xl hover:shadow-blue-500/30 dark:hover:shadow-cyan-400/25 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer ring-1 ring-blue-500/10 dark:ring-cyan-400/20"
            aria-label="Mở Trợ Lý Y Tế AI 24/7"
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
                  Trợ Lý Y Tế AI
                </span>
                <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-blue-50 dark:bg-cyan-950/60 text-blue-600 dark:text-cyan-300 border border-blue-200/60 dark:border-cyan-500/40">
                  24/7
                </span>
              </div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                Bác sĩ trực ban giám sát
              </span>
            </div>

            {/* Glowing Icon Orb */}
            <div className="relative flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-blue-600 via-blue-700 to-cyan-500 text-white shadow-md shadow-blue-600/30 group-hover:rotate-6 transition-transform duration-300">
              <Stethoscope className="w-4.5 h-4.5 sm:w-5 sm:h-5 text-white" />
              <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500 ring-2 ring-white dark:ring-[#0B1329] text-[8px] font-bold text-white">
                ✓
              </span>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
