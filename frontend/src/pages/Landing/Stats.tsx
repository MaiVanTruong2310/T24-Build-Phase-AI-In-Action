import React from 'react'
import { Activity, Clock, Users, ShieldCheck } from 'lucide-react'

export function Stats() {
  const stats = [
    {
      icon: Activity,
      value: '99.8%',
      label: 'Độ Nhạy Sàng Lọc Lâm Sàng',
      desc: 'Theo chuẩn phân loại cấp cứu quốc tế ATS & ESI',
      accentColor: 'text-blue-600 light:text-app-primary dark:text-cyan-400'
    },
    {
      icon: Clock,
      value: '< 90s',
      label: 'Thời Gian Kết Nối Bác Sĩ',
      desc: 'Trực ban chuyên khoa xử lý & phê duyệt tức thời',
      accentColor: 'text-sky-600 light:text-app-primary dark:text-blue-400'
    },
    {
      icon: Users,
      value: '120+',
      label: 'Bác Sĩ Chuyên Khoa Giám Sát',
      desc: 'Từ các Bệnh viện tuyến Trung ương hàng đầu',
      accentColor: 'text-emerald-600 dark:text-emerald-400'
    },
    {
      icon: ShieldCheck,
      value: '0%',
      label: 'Rủi Ro Bỏ Sót Ca Khẩn Cấp',
      desc: 'Hàng rào an toàn kép AI & Bác sĩ ký xác nhận',
      accentColor: 'text-teal-600 dark:text-teal-400'
    }
  ]

  return (
    <section className="bg-white light:bg-app-surface dark:bg-[#0B1329] border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white py-14 relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-0 lg:divide-x divide-slate-200 dark:divide-slate-800/80">
          {stats.map((s, i) => {
            const Icon = s.icon
            return (
              <div
                key={i}
                className="text-center px-6 py-2 transition-all duration-300 hover:bg-slate-50 light:hover:bg-app-page dark:hover:bg-slate-900/40 rounded-xl"
              >
                <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-blue-50 light:bg-app-muted dark:bg-blue-600/10 border border-blue-200 light:border-app-border dark:border-blue-500/20 mb-3 text-blue-600 light:text-app-primary dark:text-cyan-400">
                  <Icon className="w-5 h-5" />
                </div>
                <div className={`text-3xl lg:text-4xl font-bold tracking-tight mb-1.5 ${s.accentColor}`}>
                  {s.value}
                </div>
                <div className="text-sm font-semibold text-slate-800 light:text-app-text dark:text-slate-100 mb-1">
                  {s.label}
                </div>
                <div className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 leading-relaxed max-w-[220px] mx-auto">
                  {s.desc}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
