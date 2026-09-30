import { Sparkles, AlertTriangle, ShieldCheck } from 'lucide-react';
import { ChatMessage } from '../types';

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
      {/* Date Divider */}
      <div className="flex items-center justify-center my-2">
        <span className="px-3.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-semibold text-slate-500">
          Hôm nay, 08:42 AM
        </span>
      </div>

      {messages.map((message) => {
        if (message.sender === 'patient') {
          return (
            <div key={message.id} className="flex flex-col items-end space-y-1 max-w-2xl ml-auto">
              <div className="flex items-center gap-2 text-xs text-slate-500 font-semibold px-1">
                <span>{message.senderName}</span>
                <span>{message.time}</span>
              </div>
              <div className="bg-[#eaf3ff] text-slate-900 border border-sky-100 rounded-2xl rounded-tr-xs p-4 text-sm leading-relaxed shadow-2xs font-normal">
                {message.content}
              </div>
            </div>
          );
        }

        if (message.sender === 'ai') {
          return (
            <div key={message.id} className="flex flex-col items-start space-y-1.5 max-w-2xl mr-auto">
              <div className="flex items-center gap-2 text-xs font-bold text-sky-800 px-1">
                <Sparkles size={14} className="text-sky-600 shrink-0" />
                <span>{message.senderName}</span>
                {message.badge && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-100 text-sky-700 font-semibold">
                    {message.badge}
                  </span>
                )}
                <span className="text-slate-400 font-normal text-[11px]">{message.time}</span>
              </div>

              <div className="bg-white text-slate-800 border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-sm leading-relaxed shadow-2xs space-y-3">
                <p>{message.content}</p>

                {message.alertBox && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
                    <p className="text-xs font-bold text-rose-700 flex items-center gap-1.5">
                      <AlertTriangle size={14} className="text-rose-600 shrink-0" />
                      {message.alertBox.title}
                    </p>
                    <p className="text-xs text-rose-800 leading-normal font-medium">
                      {message.alertBox.description}
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        }

        // Doctor Sender
        return (
          <div key={message.id} className="flex flex-col items-end space-y-1.5 max-w-2xl ml-auto">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-800 px-1">
              <ShieldCheck size={14} className="text-teal-600 shrink-0" />
              <span>{message.senderName}</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 font-semibold">
                Bác sĩ trực ban
              </span>
              <span className="text-slate-400 font-normal text-[11px]">{message.time}</span>
            </div>

            <div className="bg-teal-700 text-white rounded-2xl rounded-tr-xs p-4 text-sm leading-relaxed shadow-xs">
              <p>{message.content}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
