import { useState } from 'react';
import { Download, AlertOctagon } from 'lucide-react';

interface WelcomeHeaderProps {
  doctorName?: string;
  shiftTime?: string;
  facilityLocation?: string;
  onExportReport?: () => void;
  onTriggerAlarm?: () => void;
}

export function WelcomeHeader({
  doctorName = 'BS. Nguyễn Phương Linh',
  shiftTime = 'Ca Sáng: 07:30 - 15:30',
  facilityLocation = 'VCare+ Sài Gòn (Khu Vực Đa Khoa Kỹ Thuật Cao)',
  onExportReport,
  onTriggerAlarm,
}: WelcomeHeaderProps) {
  const [filterMode, setFilterMode] = useState<'today' | 'shift'>('today');

  return (
    <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs mb-5">
      <div>
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-teal-50 text-teal-700 border border-teal-200">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse"></span>
            {shiftTime}
          </span>
          <span className="text-xs text-slate-500 font-medium">
            • {facilityLocation}
          </span>
        </div>

        <h1 className="text-2xl font-black text-slate-900 leading-tight">
          Chào buổi sáng, {doctorName}
        </h1>

        <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
          Hệ thống điều phối HITL đang bảo đảm 100% các ca có dấu hiệu cảnh báo lâm sàng được bác sĩ duyệt qua trước khi chuyển tiếp.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 shrink-0">
        {/* Filter Switch */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-bold">
          <button
            onClick={() => setFilterMode('today')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              filterMode === 'today'
                ? 'bg-white text-slate-800 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Hôm nay
          </button>
          <button
            onClick={() => setFilterMode('shift')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              filterMode === 'shift'
                ? 'bg-white text-slate-800 shadow-2xs font-extrabold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Ca trực này
          </button>
        </div>

        {/* Export Report */}
        <button
          onClick={onExportReport}
          className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-bold text-xs rounded-xl shadow-2xs transition-colors"
        >
          <Download size={14} />
          <span>Xuất báo cáo</span>
        </button>

        {/* Hospital Alarm */}
        <button
          onClick={onTriggerAlarm}
          className="flex items-center gap-1.5 px-4 py-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 font-extrabold text-xs rounded-xl shadow-2xs transition-colors"
        >
          <AlertOctagon size={15} className="text-rose-600" />
          <span>Bật báo động viện</span>
        </button>
      </div>
    </div>
  );
}
