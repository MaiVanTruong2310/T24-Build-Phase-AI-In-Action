import { Sparkles, ShieldCheck, Check, BadgeCheck, Activity, Shield, UserRound } from 'lucide-react';

export function BookingHeader() {
  return (
    <>
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-full text-xs font-bold border border-emerald-200">
          <Sparkles className="w-3.5 h-3.5" />
          Điều phối thông minh AI & HITL Triage
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Mã tiếp nhận: #MED-8942-VN
        </div>
      </div>

      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Đặt Lịch Khám Chuyên Khoa</h1>
          <p className="text-slate-600">Lựa chọn chuyên gia y tế, thời gian linh hoạt cùng sự bảo trợ thẩm định lâm sàng theo chuẩn y khoa.</p>
        </div>
        <div className="hidden lg:flex items-center gap-3 bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
          <div className="w-10 h-10 bg-sky-50 rounded-full flex items-center justify-center text-sky-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-slate-900 text-sm">HITL Coordinator Online</div>
            <div className="text-xs text-slate-500">Bác sĩ kiểm duyệt đơn trong &le; 15 phút</div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 lg:gap-8 mb-8 overflow-x-auto pb-4">
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0">
            <Check className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] font-bold text-emerald-600 uppercase">Bước 1</div>
            <div className="text-sm font-semibold text-slate-900">Chọn Chuyên Khoa</div>
          </div>
        </div>
        <div className="flex-1 h-px bg-slate-200 min-w-[20px]"></div>
        
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
            2
          </div>
          <div>
            <div className="text-[10px] font-bold text-sky-600 uppercase">Bước 2</div>
            <div className="text-sm font-semibold text-sky-900">Chọn Bác Sĩ & Phòng</div>
          </div>
        </div>
        <div className="flex-1 h-px bg-slate-200 min-w-[20px]"></div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
            3
          </div>
          <div>
            <div className="text-[10px] font-bold text-sky-600 uppercase">Bước 3</div>
            <div className="text-sm font-semibold text-sky-900">Khung Giờ & Hình Thức</div>
          </div>
        </div>
        <div className="flex-1 h-px bg-slate-200 min-w-[20px]"></div>

        <div className="flex items-center gap-3 shrink-0 opacity-50">
          <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center font-bold text-sm shrink-0">
            4
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase">Bước 4</div>
            <div className="text-sm font-semibold text-slate-700">Thẩm Định & Hoàn Tất</div>
          </div>
        </div>
      </div>
    </>
  )
}

export function TrustBadges() {
  return (
    <div className="mt-12 pt-8 border-t border-slate-200 grid grid-cols-2 md:grid-cols-4 gap-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-sky-50 text-sky-600 flex items-center justify-center">
          <BadgeCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-900 text-sm">Bác sĩ chuyên khoa II</div>
          <div className="text-xs text-slate-500">Trực tiếp khám & ký đơn số</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-900 text-sm">Liên thông hồ sơ HIS</div>
          <div className="text-xs text-slate-500">Đồng bộ lịch sử y tế tự động</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-900 text-sm">Chuẩn HIPAA Y Tế</div>
          <div className="text-xs text-slate-500">Mã hóa dữ liệu bệnh nhân</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center">
          <UserRound className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-900 text-sm">Trợ lý HITL 24/7</div>
          <div className="text-xs text-slate-500">Giải đáp và phân tầng rủi ro</div>
        </div>
      </div>
    </div>
  )
}
