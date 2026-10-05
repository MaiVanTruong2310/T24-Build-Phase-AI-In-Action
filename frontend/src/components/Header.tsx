import { HeaderBrand } from './HeaderBrand';
import { memo } from 'react'
import { Link } from 'react-router-dom'
import { Phone } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'

export const Header = memo(function Header() {
  return (
    <header className="flex items-center justify-between px-6 sm:px-8 py-4 relative z-10 bg-[#F8FAFC]/90 light:bg-app-page/90 dark:bg-[#0B1329]/80 backdrop-blur-md border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-800 light:text-app-text dark:text-white w-full transition-colors duration-300">
      <HeaderBrand slogan="Hệ Thống Khám Bệnh Đa Tầng Bác Sĩ Giám Sát" />
      
      <div className="flex items-center gap-4">
        <Link to="/" className="text-xs sm:text-sm font-medium text-slate-600 light:text-app-secondary dark:text-slate-300 hover:text-slate-900 light:hover:text-app-text dark:hover:text-white transition-colors hidden sm:block">
          Về trang chủ
        </Link>
        <div className="hidden sm:flex items-center gap-2 text-blue-700 light:text-app-primary dark:text-cyan-400 text-xs sm:text-sm font-medium">
          <Phone className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>Hotline: 1900 6868</span>
        </div>
        <ThemeToggle />
      </div>
    </header>
  )
})
