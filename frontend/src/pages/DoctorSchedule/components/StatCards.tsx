import { AlertTriangle, Users, Calendar, Zap, ShieldAlert } from 'lucide-react';

export const StatCards = () => (
  <div className="grid grid-cols-4 gap-4 mb-6">
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold text-slate-500 mb-1">Tổng Bác Sĩ Đang Trực Ban</p>
        <div className="flex items-end gap-2">
          <h3 className="text-3xl font-extrabold text-slate-800 leading-none">42</h3>
          <span className="text-sm font-medium text-slate-500 mb-0.5">/ 48 Nhân Sự</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-2">Bao phủ 8 chuyên khoa trọng điểm</p>
      </div>
      <div className="w-12 h-12 rounded-full bg-sky-50 flex items-center justify-center text-sky-600">
        <Users size={24} />
      </div>
    </div>

    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold text-slate-500 mb-1">Tổng Ca Khám Dự Kiến Tuần</p>
        <div className="flex items-end gap-2">
          <h3 className="text-3xl font-extrabold text-slate-800 leading-none">1.250</h3>
          <span className="text-xs font-bold text-sky-600 mb-0.5 bg-sky-50 px-2 py-0.5 rounded-full">Đạt 86% Slot</span>
        </div>
      </div>
      <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
        <Calendar size={24} />
      </div>
    </div>

    <div className="bg-rose-50 p-5 rounded-2xl border border-rose-100 shadow-sm flex items-center justify-between relative overflow-hidden">
      <div className="relative z-10">
        <p className="text-xs font-bold text-rose-600 mb-1 flex items-center gap-1.5">
          <AlertTriangle size={14} /> Cảnh Báo Quá Tải
        </p>
        <h3 className="text-xl font-extrabold text-rose-900 mb-1">Khoa Tim Mạch</h3>
        <p className="text-xs font-medium text-rose-700">Thứ 3 & Thứ 5 kín 100% (Cần mở thêm slot)</p>
      </div>
      <div className="w-12 h-12 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 relative z-10">
        <Zap size={24} />
      </div>
      <div className="absolute -right-4 -bottom-4 opacity-5 text-rose-900">
        <AlertTriangle size={100} />
      </div>
    </div>

    <div className="bg-white p-5 rounded-2xl border border-emerald-200 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-xs font-semibold text-slate-500 mb-1">Bác Sĩ Dự Phòng Tăng Cường</p>
        <div className="flex items-end gap-2">
          <h3 className="text-3xl font-extrabold text-emerald-600 leading-none">06 Bác Sĩ</h3>
          <span className="text-sm font-medium text-slate-500 mb-0.5">On-call</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-2 font-medium">Sẵn sàng nhận lệnh điều phối cấp tốc</p>
      </div>
      <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600">
        <ShieldAlert size={24} />
      </div>
    </div>
  </div>
);
