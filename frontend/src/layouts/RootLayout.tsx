import { Bell, ChevronDown, Menu, UserRound } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { BrandMark } from './BrandMark'
import { ChatbotWidget } from './ChatbotWidget'

const navItems = [
  { to: '/', label: 'Tổng quan' },
  { to: '/patient', label: 'Khu bệnh nhân' },
  { to: '/staff', label: 'Khu nhân viên' }
]

export function RootLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <div className="flex items-center gap-2">
            <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Thông báo">
              <Bell className="size-5" />
            </button>
            <button type="button" className="hidden items-center gap-2 rounded-lg p-2 text-left hover:bg-slate-100 sm:flex" aria-label="Tài khoản">
              <span className="grid size-8 place-items-center rounded-full bg-sky-100 text-sky-700"><UserRound className="size-4" /></span>
              <span className="text-sm font-medium text-slate-700">Tài khoản</span>
              <ChevronDown className="size-4 text-slate-400" />
            </button>
            <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 sm:hidden" aria-label="Mở menu">
              <Menu className="size-5" />
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 pb-3 sm:px-6 lg:px-8" aria-label="Điều hướng chính">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <ChatbotWidget />
    </div>
  )
}
