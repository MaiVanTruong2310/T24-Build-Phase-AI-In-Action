import { HourlyTrafficBar } from '../types';

interface HourlyTrafficChartProps {
  bars: HourlyTrafficBar[];
  peakTrafficText?: string;
  automationStandardText?: string;
}

export function HourlyTrafficChart({
  bars,
  peakTrafficText = 'Đỉnh lưu lượng tiếp nhận: 08:15 - 08:45 (42 ca/h)',
  automationStandardText = 'Tự động hóa đạt ngưỡng chuẩn lâm sàng cấp II',
}: HourlyTrafficChartProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-4">
      {/* Header & Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-black text-slate-900 leading-tight">
            Lưu lượng điều phối theo khung giờ
          </h3>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Tỷ lệ ca AI tự xử lý so với ca cần Bác sĩ can thiệp (HITL)
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-[#0284c7]" />
            <span className="text-slate-700">AI xử lý xong (88.5%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-[#0f766e]" />
            <span className="text-slate-700">Bác sĩ duyệt HITL (11.5%)</span>
          </div>
        </div>
      </div>

      {/* Chart visualization */}
      <div className="pt-4 pb-2">
        <div className="h-32 flex items-end justify-between gap-3 sm:gap-6 px-2 sm:px-6">
          {bars.map((bar, idx) => (
            <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
              {/* Dual bars: AI (wider/taller) and HITL (smaller) */}
              <div className="flex items-end gap-1.5 h-full w-full justify-center">
                {/* AI Bar */}
                <div
                  style={{ height: `${bar.aiHeightPercent}%` }}
                  className={`w-4 sm:w-6 rounded-t-md transition-all ${
                    bar.isProjected
                      ? 'bg-sky-200/80'
                      : bar.isCurrent
                      ? 'bg-[#0284c7] shadow-sm'
                      : 'bg-[#0284c7]/90'
                  }`}
                  title={`AI: ${bar.aiHandledPercent}%`}
                />

                {/* HITL Bar */}
                <div
                  style={{ height: `${bar.hitlHeightPercent}%` }}
                  className={`w-3 sm:w-4 rounded-t-xs transition-all ${
                    bar.isProjected
                      ? 'bg-teal-200/80'
                      : bar.isCurrent
                      ? 'bg-[#0f766e] shadow-sm'
                      : 'bg-[#0f766e]'
                  }`}
                  title={`HITL: ${bar.hitlHandledPercent}%`}
                />
              </div>

              {/* Hour Label */}
              <span
                className={`text-[11px] whitespace-nowrap text-center ${
                  bar.isCurrent
                    ? 'font-extrabold text-sky-800'
                    : 'font-medium text-slate-500'
                }`}
              >
                {bar.hour}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Meta */}
      <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 font-semibold gap-2">
        <span>{peakTrafficText}</span>
        <span className="text-teal-700">{automationStandardText}</span>
      </div>
    </div>
  );
}
