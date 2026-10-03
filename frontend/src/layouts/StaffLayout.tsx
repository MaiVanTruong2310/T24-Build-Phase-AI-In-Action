import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../app/store'
import { logoutUser } from '../features/auth/authSlice'
import { useEffect, useState } from 'react'
import { api, type Member } from '../features/coordinator/api'

const links = [
  ['/staff', 'Tổng quan'], ['/staff/queue', 'Hàng đợi điều phối'], ['/staff/chat', 'Hội thoại'],
  ['/staff/emergency', 'Cấp cứu'], ['/staff/appointments', 'Đăng ký và cọc'], ['/staff/shifts', 'Lịch khám theo buổi'],
  ['/staff/doctor-schedule', 'Lịch bác sĩ'], ['/staff/settings', 'Tài khoản và chính sách'],
  ['/staff/doctors', 'Danh mục bác sĩ'], ['/staff/specialties', 'Chuyên khoa'], ['/staff/facilities', 'Cơ sở'], ['/staff/services', 'Dịch vụ'],
]

export function StaffLayout() {
  const user = useSelector((state: RootState) => state.auth.user)
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const [admin, setAdmin] = useState(false)
  useEffect(() => { void api<Member>('/me').then(m => setAdmin(m.is_admin && !m.facility_ids.length)).catch(() => setAdmin(false)) }, [])
  return <div className="min-h-screen bg-slate-50 text-slate-800">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3"><div><strong className="text-base font-semibold">Bàn điều phối khám</strong><p className="mt-1 text-xs text-slate-500">{user?.full_name || user?.email || 'Tài khoản nhân viên'}</p></div><div className="flex gap-4 text-sm"><NavLink to="/patient">Cổng bệnh nhân</NavLink><button onClick={() => void dispatch(logoutUser()).then(() => navigate('/login'))}>Đăng xuất</button></div></header>
    <div className="mx-auto flex max-w-[1900px] flex-col lg:flex-row"><nav aria-label="Điều phối viên" className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white p-3 lg:w-56 lg:flex-shrink-0 lg:flex-col lg:border-b-0 lg:border-r">{links.filter(([to]) => admin || ['/staff', '/staff/queue', '/staff/chat', '/staff/emergency', '/staff/appointments'].includes(to)).map(([to, label]) => <NavLink end={to === '/staff'} key={to} to={to} className={({ isActive }) => 'whitespace-nowrap rounded px-3 py-2 text-sm ' + (isActive ? 'bg-slate-100 font-semibold text-slate-950' : 'text-slate-600 hover:bg-slate-50')}>{label}</NavLink>)}</nav><main className="min-w-0 flex-1"><Outlet /></main></div>
  </div>
}
