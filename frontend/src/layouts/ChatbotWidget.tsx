import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AlertTriangle,
  Bot,
  LoaderCircle,
  Maximize2,
  MessageCircle,
  Mic,
  Minimize2,
  Minus,
  RotateCcw,
  Send,
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { closeChat, toggleChat, type RootState } from '../app/store';
import {
  sendChat,
  streamChat,
  submitBooking,
  type BookingIntake,
  type ChatMetadata,
} from '../features/chat/api';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  time: string;
  pending?: boolean;
  error?: boolean;
  metadata?: ChatMetadata;
}

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  sender: 'bot',
  text: 'Chào bác, em là trợ lý tiếp đón y tế P-124. Em có thể hỗ trợ mô tả triệu chứng, định hướng chuyên khoa, tìm cơ sở, bác sĩ và lịch khám.',
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
    .replace(/\\\n/g, '\n')
    .replace(/\*\*/g, '')
    .replace(/^#{1,4}\s+/gm, '')
    .replace(/\[([^\]]+)]\((https?:\/\/[^)]+)\)/g, '$1: $2')
    .trim();
}

function atsLabel(level?: number | null, emergency?: boolean): string | null {
  if (!level) return null;
  if (emergency || level <= 2) return `ATS ${level} · Cấp cứu`;
  if (level === 3) return 'ATS 3 · Khám trong ngày';
  if (level === 4) return 'ATS 4 · Khám sớm';
  return 'ATS 5 · Không khẩn';
}

function BookingForm({ intake, sessionId }: { intake: BookingIntake; sessionId: string }) {
  const [status, setStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setStatus('Đang lưu yêu cầu…');
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
      setStatus(`Đã lưu ${result.request_code}. Điều phối viên sẽ liên hệ để xác nhận lịch.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Không thể lưu yêu cầu.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 space-y-2 rounded-xl border border-sky-100 bg-sky-50/60 p-2.5">
      <p className="font-bold text-sky-950">Phiếu yêu cầu liên hệ</p>
      <div className="grid grid-cols-2 gap-2">
        <input name="patient_name" defaultValue={intake.patient_name} required minLength={2} placeholder="Họ và tên *" className="col-span-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 outline-none focus:border-sky-500" disabled={saved} />
        <input name="patient_phone" required placeholder="Số điện thoại *" className="col-span-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 outline-none focus:border-sky-500" disabled={saved} />
        <label className="text-[10px] text-slate-500">Ngày sinh *<input name="date_of_birth" type="date" required className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs" disabled={saved} /></label>
        <label className="text-[10px] text-slate-500">Ngày muốn khám<input name="preferred_date" type="date" className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs" disabled={saved} /></label>
        <select name="preferred_doctor_id" defaultValue={intake.selected_doctor_id || ''} className="col-span-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2" disabled={saved}>
          <option value="">Để điều phối viên tư vấn bác sĩ</option>
          {(intake.doctors || []).map((doctor) => <option key={doctor.id || doctor.name} value={doctor.id}>{doctor.name} {doctor.title ? `— ${doctor.title}` : ''}</option>)}
        </select>
        <input name="facility_preference" placeholder="Cơ sở mong muốn" className="col-span-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2" disabled={saved} />
      </div>
      <label className="flex items-start gap-2 text-[10px] leading-relaxed text-slate-600">
        <input name="consent_to_contact" type="checkbox" required className="mt-0.5" disabled={saved} />
        Tôi đồng ý để bệnh viện sử dụng thông tin trên nhằm liên hệ hỗ trợ đặt lịch.
      </label>
      <button type="submit" disabled={submitting || saved} className="w-full rounded-lg bg-sky-700 px-3 py-2 font-semibold text-white disabled:opacity-60">
        {submitting ? 'Đang gửi…' : saved ? 'Đã gửi yêu cầu' : 'Gửi yêu cầu liên hệ'}
      </button>
      {status && <p className={`text-[10px] ${saved ? 'text-emerald-700' : 'text-slate-600'}`}>{status}</p>}
    </form>
  );
}

export function ChatbotWidget() {
  const dispatch = useDispatch();
  const isChatOpen = useSelector((state: RootState) => state.layout.isChatOpen);
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isSending, setIsSending] = useState(false);
  const [sessionId, setSessionId] = useState(createSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    if (isChatOpen) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isChatOpen]);

  useEffect(() => () => activeRequest.current?.abort(), []);

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
    setMessages((current) => current.map((message) => {
      if (message.id !== id) return message;
      const next = typeof update === 'function' ? update(message) : update;
      return { ...message, ...next };
    }));
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
    } catch (streamError) {
      if (request.signal.aborted) return;
      try {
        const result = await sendChat(text, sessionId, request.signal);
        updateBot(botId, { text: result.response, pending: false, metadata: result });
      } catch (fallbackError) {
        updateBot(botId, {
          text: fallbackError instanceof Error ? fallbackError.message : 'Không thể kết nối tới trợ lý. Vui lòng thử lại.',
          pending: false,
          error: true,
        });
      }
      console.warn('SSE chat fallback used', streamError);
    } finally {
      if (activeRequest.current === request) activeRequest.current = null;
      setIsSending(false);
    }
  };

  const latestQuickReplies = [...messages]
    .reverse()
    .find((message) => message.sender === 'bot' && message.metadata?.quick_replies?.length)
    ?.metadata?.quick_replies || [];

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end">
      {isChatOpen && (
        <section className={`flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl transition-all duration-200 ${isExpanded ? 'h-[85vh] w-[min(42rem,calc(100vw-2.5rem))]' : 'h-[560px] w-[min(25rem,calc(100vw-2.5rem))]'}`} aria-label="P-124 Medical Assistant">
          <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-sky-900 to-sky-800 px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15"><Bot className="h-4.5 w-4.5" /></div>
              <div><h3 className="text-xs font-bold">P-124 · Trợ lý tiếp đón y tế</h3><p className="flex items-center gap-1 text-[10px] text-white/80"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />Agent đang kết nối</p></div>
            </div>
            <div className="flex items-center gap-1 text-white/70">
              <button type="button" onClick={resetConversation} className="rounded p-1 hover:bg-white/10 hover:text-white" title="Cuộc trò chuyện mới"><RotateCcw className="h-3.5 w-3.5" /></button>
              <button type="button" onClick={() => setIsExpanded(!isExpanded)} className="rounded p-1 hover:bg-white/10 hover:text-white" title={isExpanded ? 'Thu nhỏ' : 'Mở rộng'}>{isExpanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}</button>
              <button type="button" onClick={() => dispatch(closeChat())} className="rounded p-1 hover:bg-white/10 hover:text-white" title="Đóng chat"><Minus className="h-4 w-4" /></button>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50/60 p-3.5 text-xs" aria-live="polite">
            {messages.map((message) => {
              const badge = atsLabel(message.metadata?.ats_level, message.metadata?.is_emergency);
              const candidates = message.metadata?.candidate_specialties || [];
              return (
                <div key={message.id} className={message.sender === 'user' ? 'flex justify-end' : 'flex items-start gap-2'}>
                  {message.sender === 'bot' && <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700"><Bot className="h-3.5 w-3.5" /></div>}
                  <div className={`${message.sender === 'user' ? 'max-w-[85%] rounded-2xl rounded-tr-sm bg-sky-600 px-3.5 py-2.5 text-white' : `max-w-[90%] rounded-2xl rounded-tl-sm border bg-white p-3 shadow-sm ${message.error ? 'border-red-200' : 'border-slate-200'}`}`}>
                    {badge && <div className={`mb-2 inline-flex rounded px-2 py-1 text-[9px] font-bold ${message.metadata?.is_emergency || (message.metadata?.ats_level || 5) <= 2 ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{badge}</div>}
                    {message.pending && !message.text ? <div className="flex items-center gap-2 text-slate-500"><LoaderCircle className="h-3.5 w-3.5 animate-spin" />Đang phân tích thông tin…</div> : <p className="whitespace-pre-wrap break-words leading-relaxed">{message.sender === 'bot' ? cleanAssistantText(message.text) : message.text}</p>}
                    {candidates.length > 1 && <div className="mt-2 rounded-lg border border-violet-100 bg-violet-50 p-2 text-[10px] text-violet-900"><p className="font-bold">Các chuyên khoa đang được cân nhắc</p>{candidates.slice(0, 3).map((candidate) => <p key={candidate.code || candidate.name}>• {candidate.name || candidate.code}{candidate.reason ? `: ${candidate.reason}` : ''}</p>)}</div>}
                    {message.metadata?.conflict_reason && <p className="mt-2 flex gap-1 rounded-lg bg-amber-50 p-2 text-[10px] text-amber-800"><AlertTriangle className="h-3 w-3 shrink-0" />{message.metadata.conflict_reason}</p>}
                    {message.metadata?.booking_intake?.required && <BookingForm intake={message.metadata.booking_intake} sessionId={sessionId} />}
                    {message.time && <p className={`mt-1 text-right text-[9px] ${message.sender === 'user' ? 'text-sky-200' : 'text-slate-400'}`}>{message.time}</p>}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {latestQuickReplies.length > 0 && <div className="flex gap-1.5 overflow-x-auto border-t border-slate-100 bg-white px-3 py-2 text-[11px]">{latestQuickReplies.slice(0, 4).map((reply) => <button key={reply} type="button" disabled={isSending} onClick={() => void sendMessage(reply)} className="whitespace-nowrap rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-600 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 disabled:opacity-50">{reply}</button>)}</div>}

          <form onSubmit={(event) => { event.preventDefault(); void sendMessage(inputText); }} className="flex items-center gap-2 border-t border-slate-200 bg-white p-2.5">
            <input type="text" value={inputText} disabled={isSending} onChange={(event) => setInputText(event.target.value)} placeholder="Mô tả triệu chứng hoặc nhu cầu khám…" className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800 outline-none focus:border-sky-500 focus:bg-white disabled:opacity-60" />
            <button type="button" disabled className="rounded-lg p-1.5 text-slate-300" title="Ghi âm chưa được bật"><Mic className="h-4 w-4" /></button>
            <button type="submit" disabled={isSending || !inputText.trim()} className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-700 text-white shadow hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">{isSending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}</button>
          </form>
        </section>
      )}

      {!isChatOpen && <button type="button" onClick={() => dispatch(toggleChat())} className="group flex items-center gap-2.5 rounded-full border border-slate-200 bg-white py-2 pl-3 pr-4 shadow-xl transition hover:scale-[1.02] hover:border-sky-300 hover:shadow-2xl" aria-label="Mở trợ lý P-124"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" /><span className="text-xs font-bold text-slate-800 group-hover:text-sky-700">Chat với P-124</span><span className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-700 text-white"><MessageCircle className="h-4 w-4" /></span></button>}
    </div>
  );
}
