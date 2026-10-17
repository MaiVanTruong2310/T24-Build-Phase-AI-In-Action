import { CalendarDays } from 'lucide-react';

export function SlotStatus() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-sky-600">
            <CalendarDays size={16} />
          </div>
          <h2 className="text-base font-bold text-slate-800">Tình Trạng Slot Ngày 24/10</h2>
        </div>
        <div className="text-xs font-bold text-sky-700">BS. Lê Hoàng Nam</div>
      </div>

      <p className="text-sm text-slate-600 mb-4">
        Lưới tái khám thực tế của Bác sĩ trong ca chiều. Click chọn ô để hoán đổi slot ngay lập tức:
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-slate-200 rounded-xl p-3 opacity-60">
          <div className="flex justify-between items-center mb-1">
            <span className="font-bold text-slate-800">13:30</span>
            <span className="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded">Đầy chỗ</span>
          </div>
          <p className="text-[11px] text-slate-500">Đã có 1 BN khám tái hẹn</p>
        </div>

        <div className="bg-sky-600 text-white rounded-xl p-3 shadow-md shadow-sky-200 ring-2 ring-sky-300 ring-offset-2">
          <div className="flex justify-between items-center mb-1">
            <span className="font-bold">14:15</span>
            <span className="text-[10px] font-bold text-sky-700 bg-white px-2 py-0.5 rounded">Đang giữ chỗ</span>
          </div>
          <p className="text-[11px] text-sky-100">Dành riêng cho BN An (Đang xét)</p>
        </div>

        <div className="bg-white border border-teal-200 rounded-xl p-3 cursor-pointer hover:bg-teal-50 hover:border-teal-300 transition-colors">
          <div className="flex justify-between items-center mb-1">
            <span className="font-bold text-slate-800">15:00</span>
            <span className="text-[10px] font-bold text-teal-700 bg-teal-100 px-2 py-0.5 rounded">Trống 2 chỗ</span>
          </div>
          <p className="text-[11px] text-slate-500">Có thể điều phối chuyển sang</p>
        </div>

        <div className="bg-white border border-teal-200 rounded-xl p-3 cursor-pointer hover:bg-teal-50 hover:border-teal-300 transition-colors">
          <div className="flex justify-between items-center mb-1">
            <span className="font-bold text-slate-800">16:00</span>
            <span className="text-[10px] font-bold text-teal-700 bg-teal-100 px-2 py-0.5 rounded">Trống 1 chỗ</span>
          </div>
          <p className="text-[11px] text-slate-500">Slot cuối buổi chiều</p>
        </div>
      </div>
    </div>
  );
}
