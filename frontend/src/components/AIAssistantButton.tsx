import { memo } from 'react';
import { Stethoscope } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { toggleChat } from '../app/store';

export const AIAssistantButton = memo(function AIAssistantButton() {
  const dispatch = useDispatch();

  return (
    <div className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-[9999] animate-gentle-float">
      <button
        type="button"
        onClick={() => dispatch(toggleChat())}
        className="group relative flex items-center gap-3 rounded-full border border-blue-200/90 dark:border-cyan-500/35 bg-white/95 dark:bg-[#0B1329]/95 backdrop-blur-xl py-2.5 pl-4 pr-3 shadow-xl dark:shadow-2xl shadow-blue-900/10 dark:shadow-cyan-500/15 hover:shadow-2xl hover:shadow-blue-500/30 dark:hover:shadow-cyan-400/25 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer ring-1 ring-blue-500/10 dark:ring-cyan-400/20"
        aria-label="Mở Trợ Lý Y Tế AI 24/7"
      >
        {/* Live Pulsing Status Dot */}
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
  );
});
