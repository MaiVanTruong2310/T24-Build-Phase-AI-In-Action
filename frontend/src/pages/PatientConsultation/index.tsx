import { memo } from 'react';
import { AlertTriangle, PhoneCall } from 'lucide-react';
import { ChatbotWidget } from '../../layouts/ChatbotWidget';

export default memo(function PatientConsultationPage() {
  return (
    <div className="space-y-3 pb-4 sm:space-y-4 sm:pb-6">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <h1 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
          Tư vấn triệu chứng
        </h1>
        <a
          href="tel:115"
          className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
          aria-label="Gọi cấp cứu 115 khi có dấu hiệu nguy cấp"
        >
          <PhoneCall className="h-3.5 w-3.5" />
          Cấp cứu 115
        </a>
      </div>

      <p className="flex items-start gap-1.5 px-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" />
        Nếu đau ngực dữ dội, khó thở cấp, lơ mơ hoặc yếu liệt đột ngột, hãy gọi 115 ngay.
      </p>

      <div className="h-[calc(100dvh-11.5rem)] min-h-[560px] overflow-hidden rounded-2xl border border-slate-200/90 shadow-md dark:border-slate-800/80 sm:h-[780px]">
        <ChatbotWidget embedded />
      </div>
    </div>
  );
});
