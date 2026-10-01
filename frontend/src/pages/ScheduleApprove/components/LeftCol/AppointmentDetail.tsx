import { Calendar, Stethoscope, Building2, Star } from 'lucide-react';

export function AppointmentDetail() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600">
            <Calendar size={20} />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">
              TÀI NGUYÊN TIẾP NHẬN ĐÃ CHỈ ĐỊNH
            </p>
            <h2 className="text-lg font-bold text-slate-800">Chi Tiết Lịch Hẹn Đăng Ký</h2>
          </div>
        </div>
        <div className="px-3 py-1 bg-slate-200 text-slate-700 rounded-full text-xs font-bold">
          Khám trực tiếp (In-Person)
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-100 rounded-xl p-4 flex gap-4 items-center">
          <img 
            src="https://i.pravatar.cc/150?u=dr_nam" 
            alt="Doctor" 
            className="w-16 h-16 rounded-xl object-cover border border-slate-200"
          />
          <div>
            <p className="text-[10px] font-bold text-teal-600 uppercase tracking-wider mb-0.5">
              BÁC SĨ TIẾP NHẬN CHÍNH
            </p>
            <p className="font-bold text-slate-900 text-base">BS. CKII Lê Hoàng Nam</p>
            <p className="text-xs text-slate-600 mt-0.5">Trưởng khoa Tim Mạch Can Thiệp</p>
            <div className="flex items-center gap-1 mt-1.5 text-xs text-amber-500 font-semibold">
              <Star size={12} className="fill-amber-500" />
              4.9/5 <span className="text-slate-400 font-normal">(1.280 lượt khám)</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-xl p-4 flex flex-col justify-center space-y-3">
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-sky-600 flex-shrink-0" />
            <p className="text-sm font-bold text-slate-800">14:15 - Thứ Ba, ngày 24/10/2023</p>
          </div>
          <div className="flex items-start gap-2">
            <Building2 size={16} className="text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-slate-600">
              Phòng 304 • Tầng 3 - VCare+ Tân Bình Clinic
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Stethoscope size={16} className="text-slate-400 flex-shrink-0" />
            <p>Hình thức: Khám chuyên gia & đọc ECG tại chỗ</p>
          </div>
        </div>
      </div>
    </div>
  );
}
