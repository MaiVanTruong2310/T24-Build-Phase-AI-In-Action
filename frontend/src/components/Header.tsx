import { memo } from 'react'
import { Link } from 'react-router-dom'
import { Stethoscope, Phone } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'

export const Header = memo(function Header() {
  return (
    <header className="flex items-center justify-between px-6 sm:px-8 py-4 relative z-10 bg-[#F8FAFC]/90 dark:bg-[#0B1329]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800/80 text-slate-800 dark:text-white w-full transition-colors duration-300">
      <Link to="/" className="flex items-center gap-3 transition hover:opacity-90">
        <img
          src="/vcare-logo.png"
          alt="VCare+ Logo"
          className="w-10 h-10 rounded-xl object-contain bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-700 shadow-xs shrink-0 p-0.5"
        />
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-slate-900 dark:text-slate-100 tracking-tight">VCare+</span>
            <span className="font-mono text-[10px] text-blue-700 dark:text-cyan-400 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-1.5 py-0.5 rounded">
              CLINICAL
            </span>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Hệ Thống Khám Bệnh Đa Tầng Bác Sĩ Giám Sát</p>
        </div>
      </Link>
      
      <div className="flex items-center gap-4">
        <Link to="/" className="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors hidden sm:block">
          Về trang chủ
        </Link>
        <div className="hidden sm:flex items-center gap-2 text-blue-700 dark:text-cyan-400 text-xs sm:text-sm font-medium">
          <Phone className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>Hotline: 1900 6868</span>
        </div>
        <ThemeToggle />
      </div>
    </header>
  )
})
