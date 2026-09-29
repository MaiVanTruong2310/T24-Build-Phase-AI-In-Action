import { AlertTriangle, Radio, ShieldCheck, Sliders } from 'lucide-react';

interface TopAlertBannerProps {
  urgentCount?: number;
  slaTargetSeconds?: number;
  slaCurrentSeconds?: number;
  supervisorName?: string;
  supervisorId?: string;
  streamLagMs?: number;
}

export function TopAlertBanner({
  urgentCount = 1,
  slaTargetSeconds = 90,
  slaCurrentSeconds = 24,
  supervisorName = 'BS. Nguyễn Phương Linh',
  supervisorId = 'MD-7749',
  streamLagMs = 0,
}: TopAlertBannerProps) {
  return (
    <div className="space-y-2 mb-4">
      {/* Red Critical Banner */}
      <div className="bg-rose-50 border border-rose-200 rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between text-xs text-rose-800 shadow-sm gap-2">
        <div className="flex items-center gap-2 font-bold text-rose-700">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-600"></span>
          </span>
          <AlertTriangle size={15} className="text-rose-600 shrink-0" />
          <span className="tracking-wide uppercase font-extrabold">
            TÍN HIỆU KHẨN CẤP: {urgentCount} CA CẦN TIẾP QUẢN NGAY LẬP TỨC
          </span>
        </div>

        <div className="flex items-center gap-4 flex-wrap text-slate-700 font-medium">
          <div className="flex items-center gap-1.5">
            <Radio size={14} className="text-sky-600 animate-pulse" />
            <span>
              SLA phản hồi khẩn cấp: <strong className="font-bold text-slate-900">&lt; {slaTargetSeconds} giây</strong>{' '}
              <span className="text-rose-600 font-semibold">(Hiện tại: {slaCurrentSeconds} giây)</span>
            </span>
          </div>

          <span className="text-slate-300 hidden md:inline">|</span>

          <div className="flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-600" />
            <span>
              Giám sát viên trực tiếp:{' '}
              <strong className="font-bold text-slate-900">{supervisorName}</strong>{' '}
              <span className="text-slate-500 text-[11px]">(ID: {supervisorId})</span>
            </span>
          </div>
        </div>
      </div>

      {/* Stream & Guardrails info bar */}
      <div className="flex items-center justify-between text-xs px-2 text-slate-600">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-semibold text-emerald-800">
            HITL Stream: Kết nối thời gian thực ({streamLagMs} ms lag)
          </span>
        </div>

        <button className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 transition-colors font-medium bg-white px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs hover:bg-slate-50">
          <Sliders size={13} className="text-slate-500" />
          <span>Cấu hình AI Guardrails</span>
        </button>
      </div>
    </div>
  );
}
