import { Activity, HeartPulse } from 'lucide-react'

export function Wearable() {
  return (
    <div className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="bg-slate-50 rounded-3xl p-8 lg:p-12 border border-slate-100 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-block bg-sky-100 text-sky-800 text-xs font-bold px-3 py-1.5 rounded-full mb-6 uppercase tracking-wider">
              SMART WEARABLE SYNC
            </div>
            <h2 className="text-3xl font-bold text-slate-900 mb-6">Đồng Bộ Thiết Bị Đeo Thông Minh Theo Thời Gian Thực</h2>
            <p className="text-slate-600 mb-8 leading-relaxed">
              Tự động kết nối với Apple Watch, Garmin, Samsung Health và máy đo huyết áp tại nhà. AI liên tục phân tích chỉ số sinh hiệu để phát hiện sớm rối loạn nhịp tim hoặc cơn tăng huyết áp đột ngột.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
                <Activity className="w-6 h-6 text-emerald-500 mb-3" />
                <h4 className="font-bold text-slate-900 text-sm mb-1">ECG Chuyên đạo</h4>
                <p className="text-xs text-slate-500">Phát hiện rung nhĩ (AFib) tức thì</p>
              </div>
              <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
                <HeartPulse className="w-6 h-6 text-rose-500 mb-3" />
                <h4 className="font-bold text-slate-900 text-sm mb-1">Huyết áp 24/7</h4>
                <p className="text-xs text-slate-500">Cảnh báo cơn tăng áp kịch phát</p>
              </div>
            </div>
          </div>
          
          {/* Mock UI right side */}
          <div className="bg-white rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-slate-100 relative overflow-hidden">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2 font-bold text-slate-900">
                <div className="w-6 h-6 rounded bg-slate-900 flex items-center justify-center">
                  <div className="w-2 h-2 border-2 border-white rounded-full"></div>
                </div>
                Apple Watch Series 9 • Đang đồng bộ
              </div>
              <div className="flex items-center gap-2 text-emerald-600 text-xs font-bold bg-emerald-50 px-3 py-1.5 rounded-full">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                Trực tuyến
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4 mb-8">
              <div className="text-center p-4 bg-slate-50 rounded-2xl border border-slate-100">
                <div className="text-xs font-bold text-slate-500 mb-2">Nhịp tim</div>
                <div className="text-2xl font-bold text-slate-900 mb-1">76 <span className="text-xs font-medium text-slate-500">bpm</span></div>
                <div className="text-[10px] font-bold text-emerald-600">Bình thường</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-2xl border border-slate-100">
                <div className="text-xs font-bold text-slate-500 mb-2">SpO2</div>
                <div className="text-2xl font-bold text-slate-900 mb-1">99<span className="text-xs font-medium text-slate-500">%</span></div>
                <div className="text-[10px] font-bold text-emerald-600">Tối ưu</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-2xl border border-slate-100">
                <div className="text-xs font-bold text-slate-500 mb-2">Huyết áp</div>
                <div className="text-2xl font-bold text-slate-900 mb-1">120/80</div>
                <div className="text-[10px] font-bold text-emerald-600">Chuẩn</div>
              </div>
            </div>
            
            <div className="border-t border-slate-100 pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-bold text-slate-900">Mô Phỏng Nhịp Xoang Điện Tâm Đồ (Lead II)</div>
                <div className="text-xs font-bold text-sky-600">1.0 mV / 25mm/s</div>
              </div>
              <div className="h-16 w-full flex items-center relative overflow-hidden">
                {/* SVG mock ECG line */}
                <svg viewBox="0 0 400 40" className="w-full h-full text-sky-500 stroke-current stroke-2 fill-none stroke-[3] opacity-80 animate-[pulse_2s_ease-in-out_infinite]">
                  <path d="M0,20 L50,20 L55,10 L60,35 L65,5 L70,20 L150,20 L155,10 L160,35 L165,5 L170,20 L250,20 L255,10 L260,35 L265,5 L270,20 L350,20 L355,10 L360,35 L365,5 L370,20 L400,20" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
