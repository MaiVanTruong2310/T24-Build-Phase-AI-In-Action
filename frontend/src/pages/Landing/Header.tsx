import React from 'react'
import { Bell, Settings, PlusSquare, Search, User, LogOut } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import type { RootState } from '../../app/store'
import { logout } from '../../features/auth/authSlice'

export function Header() {
  const dispatch = useDispatch();
  const { user } = useSelector((state: RootState) => state.auth);

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <div className="bg-white">
      {/* Top bar */}
      <div className="border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="bg-sky-600 text-white p-1 rounded">
                <PlusSquare className="w-6 h-6" strokeWidth={2.5} />
              </div>
              <div className="leading-tight">
                <h1 className="text-lg font-bold text-sky-800">MediCare AI</h1>
                <p className="text-[10px] text-slate-500 font-medium">Clinical Intelligence System</p>
              </div>
            </div>
            <div className="hidden md:flex items-center bg-slate-100 rounded-lg p-1">
              <button className="px-4 py-1.5 bg-white text-sky-700 text-sm font-semibold rounded-md shadow-sm">
                Cổng Bệnh Nhân
              </button>
              <button className="px-4 py-1.5 text-slate-500 text-sm font-medium hover:text-slate-700 transition-colors">
                Hệ thống Khám Bệnh Đa Tầng Bác Sĩ Giám Sát
              </button>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-full text-xs font-bold">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              Bác Sĩ Trực Ban 24/7
            </div>
            <div className="flex items-center gap-3 sm:border-l border-slate-200 sm:pl-4">
              <button className="relative text-slate-400 hover:text-slate-600 transition-colors">
                <Bell className="w-5 h-5" />
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
              </button>
              <button className="text-slate-400 hover:text-slate-600 transition-colors">
                <Settings className="w-5 h-5" />
              </button>
              {user ? (
                <div 
                  className="flex items-center gap-2 ml-2 cursor-pointer hover:bg-slate-50 p-1.5 rounded-lg transition-colors group"
                  onClick={handleLogout}
                  title="Đăng xuất"
                >
                  <img src="https://i.pravatar.cc/150?u=a042581f4e29026704d" alt="Avatar" className="w-8 h-8 rounded-full border border-slate-200 group-hover:hidden" />
                  <div className="w-8 h-8 rounded-full bg-red-100 text-red-600 hidden group-hover:flex items-center justify-center">
                    <LogOut className="w-4 h-4" />
                  </div>
                  <div className="leading-tight hidden lg:block">
                    <p className="text-xs font-bold text-slate-900">{user.name || 'Người dùng'}</p>
                    <p className="text-[10px] text-slate-500">Bệnh nhân</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3 ml-2 pl-2 border-l border-slate-200">
                  <Link to="/register" className="text-sm font-semibold text-slate-600 hover:text-sky-700 transition-colors hidden sm:block">
                    Đăng ký
                  </Link>
                  <Link 
                    to="/login"
                    className="text-sm font-semibold text-white bg-sky-600 hover:bg-sky-700 px-4 py-1.5 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <User className="w-4 h-4" />
                    <span className="hidden sm:inline">Đăng nhập</span>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Sub bar */}
      <div className="border-b border-slate-200 bg-slate-50/50">
        <div className="max-w-7xl mx-auto px-6 h-12 flex items-center justify-between overflow-x-auto">
          <nav className="flex items-center gap-6 shrink-0">
            {[
              { to: '/', label: 'Trang Chủ', end: true },
              { to: '/patient', label: 'Tư vấn AI & Bác sĩ', end: true },
              { to: '/patient/appointments', label: 'Đặt lịch khám', end: true },
              { to: '/patient/progress', label: 'Lịch hẹn & Tiến trình', end: false },
              { to: '/patient/records', label: 'Hồ sơ bệnh án', end: false }
            ].map(item => (
              <NavLink 
                key={item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `text-sm h-12 flex items-center shrink-0 transition-colors border-b-2 ${
                  isActive 
                    ? 'font-bold text-sky-700 border-sky-700' 
                    : 'font-medium text-slate-600 border-transparent hover:text-sky-700 hover:border-sky-300'
                }`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <Link to="/staff/queue" className="shrink-0 ml-6 text-xs font-semibold text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded-full hover:bg-indigo-100 transition-colors">
            Chuyển sang Bản Điều Phối Viên
          </Link>
        </div>
      </div>
    </div>
  )
}
