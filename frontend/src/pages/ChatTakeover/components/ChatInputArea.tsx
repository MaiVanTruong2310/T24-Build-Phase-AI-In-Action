import { useState, type KeyboardEvent } from 'react';
import { Paperclip, Calendar, Send, MessageSquare } from 'lucide-react';

interface ChatInputAreaProps {
  patientName: string;
  isTakenOver: boolean;
  onSendMessage: (text: string) => void;
  doctorName?: string;
}

const QUICK_CHIPS = [
  '🚑 Đang điều phối xe cấp cứu 115 đến địa chỉ nhà',
  '🫀 Hướng dẫn tư thế nằm nghỉ đầu cao 30 độ',
  '💊 Hướng dẫn ngậm 1 viên Nitroglycerin dưới lưỡi',
];

export function ChatInputArea({
  patientName,
  isTakenOver,
  onSendMessage,
  doctorName = 'BS. Nguyễn Phương Linh (Điều phối viên HITL Trực ban)',
}: ChatInputAreaProps) {
  const [inputText, setInputText] = useState('');

  const handleSend = () => {
    if (!inputText.trim()) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (chip: string) => {
    setInputText(chip);
  };

  return (
    <div className="bg-white border-t border-slate-200 p-3 rounded-b-2xl space-y-2.5">
      {/* Quick response chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="font-bold text-slate-500 shrink-0 text-[11px]">Phím tắt nhanh:</span>
        {QUICK_CHIPS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            disabled={!isTakenOver}
            onClick={() => handleChipClick(chip)}
            className="shrink-0 px-2.5 py-1 bg-slate-50 hover:bg-sky-50 text-slate-700 hover:text-sky-700 border border-slate-200 hover:border-sky-200 rounded-lg text-[11px] font-medium transition-all"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Doctor Persona indicator & helper text */}
      <div className="flex flex-wrap items-center justify-between text-xs px-1 gap-2">
        <div className="flex items-center gap-1.5 text-teal-800 font-bold">
          <MessageSquare size={14} className="text-teal-600" />
          <span>
            Bạn đang trả lời với tư cách: <strong className="font-extrabold">{doctorName}</strong>
          </span>
        </div>
        <span className="text-[11px] text-slate-400 font-normal">
          Enter để gửi • Shift + Enter xuống dòng
        </span>
      </div>

      {/* Input row */}
      <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl p-2 focus-within:bg-white focus-within:border-sky-500 focus-within:ring-1 focus-within:ring-sky-500 transition-all">
        <div className="flex items-center gap-1 text-slate-400 pb-1">
          <button
            type="button"
            title="Đính kèm tài liệu y khoa"
            className="p-1.5 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <Paperclip size={18} />
          </button>
          <button
            type="button"
            title="Tạo lịch khám nhanh"
            className="p-1.5 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <Calendar size={18} />
          </button>
        </div>

        <textarea
          rows={2}
          value={inputText}
          disabled={!isTakenOver}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Gõ chỉ định lâm sàng cho bệnh nhân ${patientName}...`}
          className="flex-1 bg-transparent text-xs text-slate-800 placeholder:text-slate-400 outline-none resize-none leading-relaxed py-1"
        />

        <button
          type="button"
          onClick={handleSend}
          disabled={!inputText.trim() || !isTakenOver}
          className="px-4 py-2 bg-sky-700 hover:bg-sky-800 disabled:opacity-40 disabled:hover:bg-sky-700 text-white text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 shrink-0 shadow-2xs"
        >
          <span>Gửi</span>
          <Send size={14} />
        </button>
      </div>

      {!isTakenOver && (
        <p className="text-[11px] text-amber-700 bg-amber-50 px-3 py-1 rounded-md border border-amber-200">
          💡 <strong>Lưu ý:</strong> Khi bạn gửi tin nhắn trực tiếp, hệ thống sẽ tự động kích hoạt chế độ Bác sĩ tiếp quản để đảm bảo an toàn lâm sàng.
        </p>
      )}
    </div>
  );
}
