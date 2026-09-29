import { useState, useRef, useEffect } from 'react';
import {
  Minus,
  Maximize2,
  Minimize2,
  Send,
  Mic,
  MessageCircle,
  Sparkles,
  Bot,
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { closeChat, toggleChat, type RootState } from '../app/store';

interface Message {
  id: string;
  sender: 'user' | 'bot' | 'doctor';
  text?: string;
  time?: string;
  doctorCard?: {
    name: string;
    avatar: string;
    slot: string;
  };
  analysisBadge?: string;
}

export function ChatbotWidget() {
  const dispatch = useDispatch();
  const isChatOpen = useSelector((state: RootState) => state.layout.isChatOpen);
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'm1',
      sender: 'user',
      text: 'Chào bác sĩ, hai ngày nay tôi tức nặng ngực trái, hơi lan ra bả vai và cánh tay. Nhờ AI tư vấn tôi có nguy hiểm không?',
      time: '10:14 AM',
    },
    {
      id: 'm2',
      sender: 'bot',
      analysisBadge: 'Cần khám sớm',
      text: 'Dấu hiệu đau ngực lan vai trái cảnh báo nguy cơ thiếu máu tim. Đề xuất: Đo ECG 12 chuyển đạo.',
      doctorCard: {
        name: 'BS. CKII Lê Hoàng Nam',
        avatar:
          'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=150',
        slot: 'Slot: 14:30 Hôm nay',
      },
      time: '10:14 AM',
    },
    {
      id: 'm3',
      sender: 'doctor',
      text: 'Tôi đã xác nhận ưu tiên slot 14:30. Chú Long vui lòng nghỉ ngơi, tránh vận động gắng sức trong lúc chờ xe đến viện.',
      time: '10:15 AM',
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isChatOpen) {
      scrollToBottom();
    }
  }, [messages, isChatOpen]);

  const handleSendMessage = () => {
    if (!inputText.trim()) return;

    const userMsg: Message = {
      id: String(Date.now()),
      sender: 'user',
      text: inputText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    // Simulated AI response
    setTimeout(() => {
      const botMsg: Message = {
        id: String(Date.now() + 1),
        sender: 'bot',
        text: 'Hệ thống đã ghi nhận thêm thông tin lâm sàng của bạn và gửi tới BS. Nguyễn Phương Linh để theo dõi sát.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    }, 1000);
  };

  const handleQuickChip = (chipText: string) => {
    setInputText(chipText);
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end">
      {/* ─── Chat Window ────────────────────────────────────────── */}
      {isChatOpen && (
        <section
          className={`flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl transition-all duration-200 ${
            isExpanded
              ? 'h-[85vh] w-[min(42rem,calc(100vw-2.5rem))]'
              : 'h-[540px] w-[min(24rem,calc(100vw-2.5rem))]'
          }`}
          aria-label="MediCare AI Chatbot"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-sky-900 to-sky-800 px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15">
                <Bot className="h-4.5 w-4.5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold tracking-tight text-white">
                    MediCare AI Chatbot
                  </h3>
                  <span className="rounded bg-emerald-500/25 px-1.5 py-0.2 text-[9px] font-bold text-emerald-300">
                    HITL 24/7
                  </span>
                </div>
                <p className="flex items-center gap-1 text-[10px] text-white/80">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  BS. Nguyễn Phương Linh giám sát
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1 text-white/70">
              <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="rounded p-1 hover:bg-white/10 hover:text-white transition"
                title={isExpanded ? 'Thu nhỏ' : 'Mở rộng'}
              >
                {isExpanded ? (
                  <Minimize2 className="h-3.5 w-3.5" />
                ) : (
                  <Maximize2 className="h-3.5 w-3.5" />
                )}
              </button>
              <button
                type="button"
                onClick={() => dispatch(closeChat())}
                className="rounded p-1 hover:bg-white/10 hover:text-white transition"
                title="Đóng chat"
              >
                <Minus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Conversation Stream */}
          <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50/60 p-3.5 text-xs">
            <div className="text-center text-[10px] font-medium text-slate-400">
              Hôm nay, 10:14 AM
            </div>

            {messages.map((msg) => (
              <div key={msg.id}>
                {/* 1. Patient message */}
                {msg.sender === 'user' && (
                  <div className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-sky-600 px-3.5 py-2.5 text-white shadow-sm">
                      <p className="leading-relaxed">{msg.text}</p>
                      {msg.time && (
                        <p className="mt-1 text-right text-[9px] text-sky-200">
                          {msg.time}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. AI Bot message */}
                {msg.sender === 'bot' && (
                  <div className="flex items-start gap-2 max-w-[90%]">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-700 mt-1">
                      <Bot className="h-3.5 w-3.5" />
                    </div>
                    <div className="space-y-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-3 shadow-sm">
                      {msg.analysisBadge && (
                        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                          <span className="flex items-center gap-1 font-bold text-slate-800 text-[11px]">
                            <Sparkles className="h-3 w-3 text-sky-600" />
                            Phân tích lâm sàng
                          </span>
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold text-amber-800">
                            {msg.analysisBadge}
                          </span>
                        </div>
                      )}

                      <p className="leading-relaxed text-slate-700 font-medium">
                        {msg.text}
                      </p>

                      {msg.doctorCard && (
                        <div className="flex items-center justify-between rounded-xl border border-sky-100 bg-sky-50/50 p-2.5">
                          <div className="flex items-center gap-2">
                            <img
                              src={msg.doctorCard.avatar}
                              alt={msg.doctorCard.name}
                              className="h-8 w-8 rounded-lg object-cover border border-slate-200"
                            />
                            <div>
                              <p className="font-bold text-slate-900 text-[11px]">
                                {msg.doctorCard.name}
                              </p>
                              <p className="text-[10px] text-slate-500">
                                {msg.doctorCard.slot}
                              </p>
                            </div>
                          </div>
                          <button
                            type="button"
                            className="rounded-lg bg-sky-700 px-2.5 py-1 text-[11px] font-semibold text-white shadow-sm hover:bg-sky-800"
                          >
                            Đặt ngay
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. Doctor note message */}
                {msg.sender === 'doctor' && (
                  <div className="ml-8 rounded-xl border border-emerald-200 bg-emerald-50/70 p-2.5 text-[11px]">
                    <p className="font-bold text-emerald-900">
                      BS. Nguyễn Phương Linh (HITL):
                    </p>
                    <p className="mt-0.5 text-slate-700 italic leading-relaxed">
                      "{msg.text}"
                    </p>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Chips */}
          <div className="flex items-center gap-1.5 border-t border-slate-100 bg-white px-3 py-2 overflow-x-auto text-[11px]">
            {['Đặt hẹn 14:30', 'Lưu ý trước khám', 'Gặp bác sĩ'].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => handleQuickChip(chip)}
                className="whitespace-nowrap rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-600 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="flex items-center gap-2 border-t border-slate-200 bg-white p-2.5">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Hỏi triệu chứng y tế..."
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white"
            />
            <button
              type="button"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              title="Ghi âm câu hỏi"
            >
              <Mic className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={handleSendMessage}
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-700 text-white shadow transition hover:bg-sky-800 active:scale-95"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </section>
      )}

      {/* ─── Floating Trigger Pill Button (When chat is closed) ──── */}
      {!isChatOpen && (
        <button
          type="button"
          onClick={() => dispatch(toggleChat())}
          className="group flex items-center gap-2.5 rounded-full border border-slate-200 bg-white py-2 pl-3 pr-4 shadow-xl transition-all hover:shadow-2xl hover:border-sky-300 hover:scale-[1.02] active:scale-95"
          aria-label="Mở Chatbot AI MediCare"
        >
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-slate-800 group-hover:text-sky-700">
            Chat với AI MediCare
          </span>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-700 text-white shadow-sm relative">
            <MessageCircle className="h-4 w-4" />
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white border-2 border-white">
              1
            </span>
          </div>
        </button>
      )}
    </div>
  );
}
