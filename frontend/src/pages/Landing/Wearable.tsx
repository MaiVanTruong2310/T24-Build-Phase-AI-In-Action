import React from 'react'
import { Activity, HeartPulse, Watch } from 'lucide-react'

export function Wearable() {
  return (
    <section className="py-24 bg-slate-50 light:bg-app-page dark:bg-[#070D1E] border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="bg-white light:bg-app-surface dark:bg-slate-900/60 rounded-3xl p-8 lg:p-12 border border-slate-200 light:border-app-border dark:border-slate-800/80 grid lg:grid-cols-2 gap-12 items-center reveal-item shadow-xs dark:shadow-none">
          <div>
<h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-6 tracking-tight">
              Giám Sát Chỉ Số Sinh Hiệu Người Bệnh Liên Tục 24/7
            </h2>
            <p className="text-slate-600 light:text-app-secondary dark:text-slate-400 text-sm lg:text-base mb-8 leading-relaxed">
              Tự động kết nối với Apple Watch, Garmin, Samsung Health và máy đo huyết áp tại nhà. AI liên tục phân tích biến thiên nhịp tim (HRV) và huyết động học để cảnh báo sớm nguy cơ trước khi biến chứng bùng phát.
            </p>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="bg-slate-50 light:bg-app-page dark:bg-slate-950/60 p-4 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-800/80 hover:border-cyan-500/30 light:hover:border-app-primary/30 transition-all">
                <Activity className="w-6 h-6 text-blue-600 light:text-app-primary dark:text-cyan-400 mb-3" />
                <h4 className="font-semibold text-slate-900 light:text-app-text dark:text-slate-100 text-sm mb-1">Điện Tâm Đồ (ECG)</h4>
                <p className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 leading-relaxed">Phát hiện rung nhĩ (AFib) và ngoại tâm thu thất tức thì</p>
              </div>

              <div className="bg-slate-50 light:bg-app-page dark:bg-slate-950/60 p-4 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-800/80 hover:border-blue-500/30 light:hover:border-app-primary/30 transition-all">
                <HeartPulse className="w-6 h-6 text-blue-600 light:text-app-primary dark:text-blue-400 mb-3" />
                <h4 className="font-semibold text-slate-900 light:text-app-text dark:text-slate-100 text-sm mb-1">Huyết Áp 24/7</h4>
                <p className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 leading-relaxed">Cảnh báo cơn tăng huyết áp kịch phát ban đêm</p>
              </div>
            </div>
          </div>
          
          {/* Mock Clinical Monitor UI */}
          <div className="bg-slate-100 light:bg-app-muted dark:bg-slate-950/80 rounded-2xl p-6 sm:p-7 border border-slate-200 light:border-app-border dark:border-slate-800/90 shadow-lg dark:shadow-2xl relative overflow-hidden">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2.5 font-medium text-slate-800 light:text-app-text dark:text-slate-200 text-xs sm:text-sm">
                <div className="w-6 h-6 rounded-lg bg-blue-100 light:bg-app-tint dark:bg-blue-600/20 border border-blue-300 dark:border-blue-500/30 flex items-center justify-center text-blue-600 light:text-app-primary dark:text-cyan-400">
                  <Watch className="w-3.5 h-3.5" />
                </div>
                <span>Thiết bị đeo thông minh • Đang đồng bộ</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-500/30 px-3 py-1 rounded-lg">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Trực Tuyến</span>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-3.5 mb-8">
              <div className="text-center p-3.5 bg-white light:bg-app-surface dark:bg-slate-900/60 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-800/80 shadow-xs">
                <div className="text-[11px] text-slate-500 light:text-app-secondary dark:text-slate-400 mb-1">Nhịp tim</div>
                <div className="text-xl sm:text-2xl font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-1 font-mono">
                  76 <span className="text-xs font-normal text-slate-400 light:text-app-secondary">bpm</span>
                </div>
                <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase">Ổn định</div>
              </div>

              <div className="text-center p-3.5 bg-white light:bg-app-surface dark:bg-slate-900/60 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-800/80 shadow-xs">
                <div className="text-[11px] text-slate-500 light:text-app-secondary dark:text-slate-400 mb-1">SpO2</div>
                <div className="text-xl sm:text-2xl font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-1 font-mono">
                  99<span className="text-xs font-normal text-slate-400 light:text-app-secondary">%</span>
                </div>
                <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase">Tối ưu</div>
              </div>

              <div className="text-center p-3.5 bg-white light:bg-app-surface dark:bg-slate-900/60 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-800/80 shadow-xs">
                <div className="text-[11px] text-slate-500 light:text-app-secondary dark:text-slate-400 mb-1">Huyết áp</div>
                <div className="text-xl sm:text-2xl font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-1 font-mono">
                  120/80
                </div>
                <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase">Chuẩn y khoa</div>
              </div>
            </div>
            
            <div className="border-t border-slate-200 light:border-app-border dark:border-slate-800/80 pt-5">
              <div className="flex items-center justify-between mb-3 text-xs">
                <span className="font-medium text-slate-700 light:text-app-text dark:text-slate-300">Điện Tâm Đồ Thời Gian Thực (ECG Lead II)</span>
                <span className="text-blue-600 light:text-app-primary dark:text-cyan-400 font-mono text-[11px]">1.0 mV • 25mm/s</span>
              </div>
              <div className="h-14 w-full flex items-center relative overflow-hidden bg-white light:bg-app-surface dark:bg-slate-900/40 rounded-lg px-2 border border-slate-200 light:border-app-border dark:border-slate-800/60">
                {/* SVG mock ECG line */}
                <svg viewBox="0 0 400 40" className="w-full h-full text-blue-600 light:text-app-primary dark:text-cyan-400 stroke-current stroke-2 fill-none opacity-85">
                  <path d="M0,20 L50,20 L55,10 L60,35 L65,5 L70,20 L150,20 L155,10 L160,35 L165,5 L170,20 L250,20 L255,10 L260,35 L265,5 L270,20 L350,20 L355,10 L360,35 L365,5 L370,20 L400,20" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
