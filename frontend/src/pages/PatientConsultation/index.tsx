import { memo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { ChatbotWidget } from '../../layouts/ChatbotWidget';
import { SosButton } from '../../features/chat/SosButton';

export default memo(function PatientConsultationPage() {
  return (
    <div className="space-y-3 pb-4 sm:space-y-4 sm:pb-6">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <h1 className="text-base font-bold text-slate-900 dark:text-white sm:text-lg">
          Tư vấn triệu chứng
        </h1>
        <SosButton variant="pill" />
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
