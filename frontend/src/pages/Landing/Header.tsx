import React from 'react';
import { Bell, Settings, PlusSquare, LogOut, MessageSquare, Calendar, Clock, FileText, ArrowRightLeft, User } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../../app/store';
import { logoutUser } from '../../features/auth/authSlice';
import { getUserAvatarUrl } from '../../features/auth/session';

export function Header() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);

  const handleLogout = () => {
    dispatch(logoutUser());
  };

  // Demo fallback user matching the screenshot
  const displayUser = user || {
    full_name: 'Nguyễn Văn An',
    role: 'patient',
  };

  return (
    <div className="bg-white">
      {/* ─── Top bar ────────────────────────────────────────────── */}
      <div className="border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2 transition hover:opacity-90">
              <div className="bg-sky-600 text-white p-1 rounded">
                <PlusSquare className="w-6 h-6" strokeWidth={2.5} />
              </div>
              <div className="leading-tight">
                <h1 className="text-lg font-bold text-sky-800">MediCare AI</h1>
                <p className="text-[10px] text-slate-500 font-medium">Clinical Intelligence System</p>
              </div>
            </Link>

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
              HITL Active 24/7
            </div>

            <div className="flex items-center gap-3 sm:border-l border-slate-200 sm:pl-4">
              <button className="relative text-slate-400 hover:text-slate-600 transition-colors p-1" title="Thông báo">
                <Bell className="w-5 h-5" />
                <span className="absolute -top-0.5 -right-1 w-4 h-4 bg-red-500 rounded-full border border-white text-white text-[9px] font-bold flex items-center justify-center">
                  3
                </span>
              </button>

              <button className="text-slate-400 hover:text-slate-600 transition-colors p-1" title="Cài đặt">
                <Settings className="w-5 h-5" />
              </button>

              {/* User profile */}
          {user ? (
            <div
              className="flex items-center gap-2 ml-2 cursor-pointer hover:bg-slate-50 p-1.5 rounded-lg transition-colors group"
              onClick={handleLogout}
              title="Đăng xuất"
            >
              <img 
                src={getUserAvatarUrl(user)} 
                alt={user.full_name} 
                className="w-8 h-8 rounded-full border border-slate-200 group-hover:hidden object-cover" 
              />
              <div className="w-8 h-8 rounded-full bg-red-100 text-red-600 hidden group-hover:flex items-center justify-center">
                <LogOut className="w-4 h-4" />
              </div>
              <div className="leading-tight hidden lg:block">
                <p className="text-xs font-bold text-slate-900">{user.full_name || 'Người dùng'}</p>
                <p className="text-[10px] text-slate-500">{user.role === 'staff' ? 'Nhân viên' : 'Bệnh nhân'}</p>
              </div>
            </div>
              
                </div>
                <div className="leading-tight hidden lg:block text-left">
                  <p className="text-xs font-bold text-slate-900">{displayUser.full_name}</p>
                  <p className="text-[10px] text-slate-500">Bệnh nhân</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* ─── Sub bar (Navigation tabs) ─────────────────────────── */}
      <div className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 h-13 py-2 flex items-center justify-between overflow-x-auto">
          <nav className="flex items-center gap-1.5 shrink-0">
            {[
              { to: '/', label: 'Trang Chủ', end: true, icon: null },
              { to: '/patient', label: 'Tư vấn AI & Bác sĩ', end: true, icon: MessageSquare },
              { to: '/patient/appointments', label: 'Đặt lịch khám', end: true, icon: Calendar },
              { to: '/patient/progress', label: 'Lịch hẹn & Tiến trình', end: false, icon: Clock },
              { to: '/patient/profile', label: 'Hồ sơ bệnh án', end: false, icon: FileText }
            ].map(item => (
              <NavLink 
                key={item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `text-xs sm:text-sm font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 shrink-0 transition-all ${
                  isActive 
                    ? 'bg-sky-600 text-white shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {item.icon && <item.icon className="w-3.5 h-3.5" />}
                {item.label}
              </NavLink>
            ))}
          </nav>

          <Link 
            to="/staff/queue" 
            className="shrink-0 ml-6 text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 px-3 py-1.5 rounded-lg hover:bg-indigo-100 transition-colors flex items-center gap-1.5"
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Chuyển sang Bản Điều Phối Viên</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
