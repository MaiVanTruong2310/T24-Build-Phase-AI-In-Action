import { Sparkles, Check, ShieldCheck, ArrowRightLeft, ChevronRight } from 'lucide-react';

export function DoctorCard() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-slate-900 flex items-center gap-2">
          2. Bác Sĩ Chuyên Trách
        </h2>
        <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">Đang Phụ Trách</span>
      </div>
      
      <div className="bg-white rounded-2xl border border-sky-100 shadow-sm overflow-hidden relative">
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-sky-400 to-emerald-400"></div>
        <div className="p-4">
          <div className="inline-flex items-center gap-1.5 bg-sky-50 text-sky-700 text-xs font-semibold px-2.5 py-1 rounded-md mb-4">
            <Sparkles className="w-3.5 h-3.5" /> AI đề xuất dựa trên triệu chứng tức ngực
          </div>
          
          <div className="flex gap-4 mb-4">
            <div className="relative shrink-0">
              <img src="https://i.pravatar.cc/150?img=11" alt="Doctor" className="w-14 h-14 rounded-xl object-cover border border-slate-200" />
              <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-white flex items-center justify-center text-white">
                <Check className="w-2.5 h-2.5" />
              </div>
            </div>
            <div>
              <div className="font-bold text-slate-900 text-sm">BS. CKII Lê Hoàng Nam</div>
              <div className="text-sky-600 text-xs font-medium mb-1.5">Trưởng khoa Tim mạch Can thiệp</div>
              <div className="flex items-center gap-3 text-[11px] text-slate-500">
                <div className="flex items-center gap-1">
                  <span className="text-amber-500 font-bold">★ 4.9</span>
                  <span>(142 đánh giá)</span>
                </div>
                <div className="w-1 h-1 rounded-full bg-slate-300"></div>
                <div>18 năm kinh nghiệm</div>
              </div>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-3 flex items-center justify-between">
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Phí khám chuyên khoa</div>
              <div className="font-bold text-sky-700 text-lg">350.000 VNĐ</div>
            </div>
            <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded">
              <ShieldCheck className="w-3.5 h-3.5" /> BHYT hỗ trợ 80%
            </div>
          </div>
        </div>
        
        <button className="w-full py-3 border-t border-slate-100 text-xs font-semibold text-slate-600 hover:bg-slate-50 hover:text-sky-600 transition-colors flex items-center justify-center gap-2">
          <ArrowRightLeft className="w-3.5 h-3.5" /> Đổi bác sĩ chuyên khoa khác (3 BS trống lịch) <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
