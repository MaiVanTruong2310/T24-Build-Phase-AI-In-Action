import { CalendarClock, ClipboardList, CreditCard, HeartPulse, LayoutDashboard, Menu, MessageSquareText, PanelLeftClose, PanelLeftOpen, Settings, ShieldCheck, Stethoscope, UsersRound, X } from 'lucide-react'
import { useEffect, useState, type Dispatch, type SetStateAction } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../app/store'
import { logoutUser } from '../features/auth/authSlice'
import { api, canAdminister, type Member } from '../features/coordinator/api'

const navItems = [
  { to: '/staff', label: 'Tổng quan', icon: LayoutDashboard, group: 'Điều phối' },
  { to: '/staff/queue', label: 'Hàng đợi điều phối', icon: ClipboardList, group: 'Điều phối' },
  { to: '/staff/chat', label: 'Hội thoại', icon: MessageSquareText, group: 'Điều phối' },
  { to: '/staff/emergency', label: 'Cấp cứu', icon: HeartPulse, group: 'Điều phối' },
  { to: '/staff/appointments', label: 'Đăng ký và cọc', icon: CreditCard, group: 'Điều phối' },
  { to: '/staff/booking-approvals', label: 'Duyệt lịch khám', icon: CalendarClock, group: 'Điều phối' },
  { to: '/staff/patients', label: 'Hồ sơ bệnh nhân', icon: UsersRound, group: 'Điều phối' },
  { to: '/staff/shifts', label: 'Lịch khám theo buổi', icon: CalendarClock, group: 'Quản trị', admin: true },
  { to: '/staff/doctor-schedule', label: 'Lịch bác sĩ', icon: CalendarClock, group: 'Điều phối' },
  { to: '/staff/doctors', label: 'Danh mục bác sĩ', icon: Stethoscope, group: 'Quản trị', admin: true },
  { to: '/staff/services', label: 'Dịch vụ', icon: UsersRound, group: 'Quản trị', admin: true },
  { to: '/staff/settings', label: 'Tài khoản và chính sách', icon: Settings, group: 'Quản trị', admin: true },
]
const groups = ['Điều phối', 'Quản trị']
export interface StaffContext { member: Member; updateMember: Dispatch<SetStateAction<Member | null>> }

export function StaffLayout() {
  const user = useSelector((state: RootState) => state.auth.user)
  const dispatch = useDispatch<AppDispatch>(); const navigate = useNavigate()
  const [member, setMember] = useState<Member | null>(null); const [accessError, setAccessError] = useState(''); const [retry, setRetry] = useState(0)
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false)
  useEffect(() => {
    let active = true
    setMember(null); setAccessError('')
    const refresh = async () => {
      try { const value = await api<Member>('/me'); if (active) { setMember(value); setAccessError('') } }
      catch (error) { if (active) { setMember(null); setAccessError(error instanceof Error ? error.message : 'Không thể kiểm tra quyền điều phối.') } }
    }
    const refreshOnTokenRenewal = () => { void refresh() }
    window.addEventListener('auth:refreshed', refreshOnTokenRenewal)
    void refresh(); return () => { active = false; window.removeEventListener('auth:refreshed', refreshOnTokenRenewal) }
  }, [user?.id, retry])
  const admin = canAdminister(member); const available = navItems.filter((item) => admin || !item.admin)
  const displayName = user?.full_name || user?.email || 'Tài khoản nhân viên'
  const initials = displayName.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const logout = () => void dispatch(logoutUser()).then(() => navigate('/login'))
  const sidebar = (mobile = false) => (
    <aside aria-label="Điều hướng nhân viên" className={`flex h-full flex-col border-r border-slate-200 bg-white shadow-[1px_0_18px_rgba(15,23,42,0.03)] ${mobile ? 'w-72' : collapsed ? 'w-20' : 'w-72'} transition-[width] duration-200`}>
      <div className="flex h-[84px] items-center gap-3 border-b border-slate-100 px-4"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-700 text-sm font-bold text-white">VC</div>{(!collapsed || mobile) && <div className="min-w-0"><p className="truncate text-sm font-bold text-slate-900">Bàn điều phối khám</p><p className="mt-0.5 text-xs text-slate-500">VCare+ Staff Portal</p></div>}{mobile && <button type="button" onClick={() => setMobileOpen(false)} className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Đóng điều hướng"><X size={18} /></button>}</div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-5">{groups.map((group) => { const items = available.filter((item) => item.group === group); return items.length ? <div key={group} className="mb-6">{(!collapsed || mobile) && <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">{group}</p>}<div className="space-y-1">{items.map(({ to, label, icon: Icon }) => <NavLink end={to === '/staff'} key={to} to={to} onClick={() => setMobileOpen(false)} title={collapsed && !mobile ? label : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${isActive ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-100' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950'} ${collapsed && !mobile ? 'justify-center px-2' : ''}`}><Icon size={19} strokeWidth={1.8} className="shrink-0" />{(!collapsed || mobile) && <span className="truncate">{label}</span>}</NavLink>)}</div></div> : null })}</nav>
      <div className="border-t border-slate-100 p-3"><div className={`flex items-center gap-3 rounded-xl bg-slate-50 p-3 ${collapsed && !mobile ? 'justify-center p-2' : ''}`}><div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-800">{initials}</div>{(!collapsed || mobile) && <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{displayName}</p><p className="mt-0.5 flex items-center gap-1 text-xs text-emerald-700"><ShieldCheck size={12} /> Nhân viên điều phối</p></div>}</div>{(!collapsed || mobile) && <button type="button" onClick={logout} className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-600 hover:bg-rose-50 hover:text-rose-700">Đăng xuất</button>}</div>
    </aside>
  )
  return <div className="min-h-screen bg-slate-50 text-slate-800"><div className="hidden min-h-screen lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:flex">{sidebar()}</div><div className={`${collapsed ? 'lg:pl-20' : 'lg:pl-72'} min-h-screen transition-[padding] duration-200`}><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur lg:px-7"><div className="flex items-center gap-3"><button type="button" onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Mở điều hướng"><Menu size={21} /></button><button type="button" onClick={() => setCollapsed((value) => !value)} className="hidden rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:inline-flex" aria-label={collapsed ? 'Mở rộng điều hướng' : 'Thu gọn điều hướng'}>{collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}</button><div><p className="text-sm font-semibold text-slate-900">Không gian điều phối</p><p className="hidden text-xs text-slate-500 sm:block">Theo dõi ca khám và hỗ trợ bệnh nhân</p></div></div><button type="button" onClick={logout} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-rose-50 hover:text-rose-700">Đăng xuất</button></header><main className="min-w-0">{accessError ? <div className="p-5 lg:p-7"><p role="alert" className="text-rose-700">{accessError}</p><button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-3 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50">Thử lại</button></div> : !member ? <p className="p-5 text-sm text-slate-600 lg:p-7">Đang kiểm tra quyền điều phối…</p> : <Outlet context={{ member, updateMember: setMember }} />}</main></div>{mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button type="button" aria-label="Đóng điều hướng" className="absolute inset-0 bg-slate-950/35" onClick={() => setMobileOpen(false)} /><div className="relative h-full">{sidebar(true)}</div></div>}</div>
}
