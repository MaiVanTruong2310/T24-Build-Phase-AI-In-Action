import { Activity, ClipboardList, LayoutDashboard, UsersRound } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

const items = [
  { to: '/staff', label: 'Tổng quan', icon: LayoutDashboard, end: true },
  { to: '/staff/queue', label: 'Điều phối hàng đợi', icon: ClipboardList },
  { to: '/staff/patients', label: 'Quản lý bệnh nhân', icon: UsersRound },
  { to: '/staff/monitoring', label: 'Giám sát hệ thống', icon: Activity }
]

export function StaffLayout() {
  return (
    <div className="grid gap-6 lg:grid-cols-[15rem_1fr]">
      <aside className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
        <p className="px-3 pb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Khu nhân viên</p>
        <nav className="grid gap-1" aria-label="Điều hướng nhân viên">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <section className="min-w-0">
        <Outlet />
      </section>
    </div>
  )
}
