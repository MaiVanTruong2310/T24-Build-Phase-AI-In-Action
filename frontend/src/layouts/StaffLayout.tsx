import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../app/store'
import { logoutUser } from '../features/auth/authSlice'
import { useEffect, useState, type Dispatch, type SetStateAction } from 'react'
import { api, canAdminister, type Member } from '../features/coordinator/api'

const links = [
  ['/staff', 'Tổng quan'], ['/staff/queue', 'Hàng đợi điều phối'], ['/staff/chat', 'Hội thoại'],
  ['/staff/emergency', 'Cấp cứu'], ['/staff/appointments', 'Đăng ký và cọc'], ['/staff/booking-approvals', 'Duyệt lịch khám'], ['/staff/shifts', 'Lịch khám theo buổi'],
  ['/staff/doctor-schedule', 'Lịch bác sĩ'], ['/staff/settings', 'Tài khoản và chính sách'],
  ['/staff/doctors', 'Danh mục bác sĩ'], ['/staff/services', 'Dịch vụ'],
]

export interface StaffContext { member: Member; updateMember: Dispatch<SetStateAction<Member | null>> }

export function StaffLayout() {
  const user = useSelector((state: RootState) => state.auth.user)
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const [member, setMember] = useState<Member | null>(null)
  const [accessError, setAccessError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout>
    setMember(null); setAccessError('')
    const refresh = async () => {
      try { const value = await api<Member>('/me'); if (active) { setMember(value); setAccessError('') } }
      catch (e) { if (active) { setMember(null); setAccessError(e instanceof Error ? e.message : 'Không thể kiểm tra quyền điều phối.') } }
      if (active) timer = setTimeout(refresh, 30000)
    }
    void refresh()
    return () => { active = false; clearTimeout(timer) }
  }, [user?.id, retry])
  const admin = canAdminister(member)
  return <div className="min-h-screen bg-slate-50 text-slate-800">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3"><div><strong className="text-base font-semibold">Bàn điều phối khám</strong><p className="mt-1 text-xs text-slate-500">{user?.full_name || user?.email || 'Tài khoản nhân viên'}</p></div><div className="flex gap-4 text-sm"><button onClick={() => void dispatch(logoutUser()).then(() => navigate('/login'))}>Đăng xuất</button></div></header>
    <div className="mx-auto flex max-w-[1900px] flex-col lg:flex-row"><nav aria-label="Điều phối viên" className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white p-3 lg:w-56 lg:flex-shrink-0 lg:flex-col lg:border-b-0 lg:border-r">{links.filter(([to]) => admin || ['/staff', '/staff/queue', '/staff/chat', '/staff/emergency', '/staff/appointments', '/staff/booking-approvals'].includes(to)).map(([to, label]) => <NavLink end={to === '/staff'} key={to} to={to} className={({ isActive }) => 'whitespace-nowrap rounded px-3 py-2 text-sm ' + (isActive ? 'bg-slate-100 font-semibold text-slate-950' : 'text-slate-600 hover:bg-slate-50')}>{label}</NavLink>)}</nav><main className="min-w-0 flex-1">{accessError ? <div className="p-5"><p role="alert" className="text-red-700">{accessError}</p><button onClick={() => setRetry(value => value + 1)}>Thử lại</button></div> : !member ? <p className="p-5">Đang kiểm tra quyền điều phối…</p> : <Outlet context={{ member, updateMember: setMember }} />}</main></div>
  </div>
}
