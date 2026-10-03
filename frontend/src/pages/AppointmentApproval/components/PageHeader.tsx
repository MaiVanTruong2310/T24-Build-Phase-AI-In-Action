import { CalendarCheck, RefreshCw } from 'lucide-react';
import type { BookingCounts } from './constants';
import { SummaryCard } from './SummaryCard';

interface PageHeaderProps {
  counts: BookingCounts;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function PageHeader({ counts, isRefreshing, onRefresh }: PageHeaderProps) {
  return (
    <div className="bg-white border-b border-slate-200 px-6 py-5 flex-shrink-0">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sky-500 to-sky-700 flex items-center justify-center text-white shadow-lg shadow-sky-200">
            <CalendarCheck size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Duyệt Lịch Hẹn Khám Bệnh
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              HITL Coordinator — Phê duyệt & điều phối lịch hẹn bệnh nhân trong hệ thống VCare+
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 text-slate-700 font-semibold text-sm rounded-xl hover:bg-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            Làm mới
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
        <SummaryCard
          label="Chờ duyệt"
          value={counts.pending_approval}
          accent="text-amber-600"
          bg="bg-amber-50"
          border="border-amber-100"
          dot="bg-amber-500 animate-pulse"
        />
        <SummaryCard
          label="Đã duyệt hôm nay"
          value={counts.confirmed}
          accent="text-emerald-600"
          bg="bg-emerald-50"
          border="border-emerald-100"
          dot="bg-emerald-500"
        />
        <SummaryCard
          label="Đã từ chối"
          value={counts.rejected}
          accent="text-rose-600"
          bg="bg-rose-50"
          border="border-rose-100"
          dot="bg-rose-500"
        />
        <SummaryCard
          label="Tổng lịch hẹn"
          value={counts.all}
          accent="text-sky-600"
          bg="bg-sky-50"
          border="border-sky-100"
          dot="bg-sky-500"
        />
      </div>
    </div>
  );
}
