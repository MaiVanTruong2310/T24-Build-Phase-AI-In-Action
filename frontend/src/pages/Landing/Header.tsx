import { HeaderBrand } from '../../components/HeaderBrand';
import { LogoutButton } from '../../components/LogoutButton';
import React, { useState } from 'react';
import './Header.css';

import {
  Calendar,
  Clock,
  FileText,
  MessageSquare,
  Search,
  ShieldCheck,
  User,
} from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../../app/store';
import { logoutUser } from '../../features/auth/authSlice';
import { PatientAvatar } from '../../components/PatientAvatar';
import { NotificationBell } from '../../features/notification/NotificationBell';
import { ThemeToggle } from '../../components/ThemeToggle';

export function Header() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const [menuOpen, setMenuOpen] = useState(() => window.matchMedia('(min-width: 640px)').matches);

  const handleLogout = () => {
    dispatch(logoutUser());
    setMenuOpen(false);
  };

  const navItems = [
    { to: '/', label: 'Trang Chủ', end: true, icon: null },
    { to: '/patient', label: 'Tư Vấn AI & Bác Sĩ', end: true, icon: MessageSquare },
    { to: '/patient/doctors', label: 'Tìm Bác Sĩ', end: true, icon: Search },
    { to: '/patient/appointments', label: 'Đặt lịch khám', end: true, icon: Calendar },
    ...(user
      ? [
          { to: '/patient/progress', label: 'Tiến Trình Điều Trị', end: false, icon: Clock },
          { to: '/patient/profile', label: 'Hồ Sơ Bệnh Án', end: false, icon: FileText },
        ]
      : []),
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#F8FAFC]/90 light:bg-app-page/90 dark:bg-[#0B1329]/90 backdrop-blur-md border-b border-slate-200 light:border-app-border dark:border-slate-800/80 transition-colors duration-300">
      {/* ─── Top bar ────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-2 sm:gap-8">
          <HeaderBrand />

        </div>

        <div className="flex items-center gap-1.5 sm:gap-3 sm:border-l border-slate-200 light:border-app-border sm:pl-4">
          <NotificationBell enabled={Boolean(user)} />
          <div className="flex items-center gap-2 sm:gap-3">

            {/* Theme Toggle Button (Light / Dark) */}
            <ThemeToggle />

            {/* User profile (Desktop) */}
            <div className="hidden sm:flex items-center gap-3 sm:border-l border-slate-200 light:border-app-border dark:border-slate-800 sm:pl-3">
              {user ? (
                <div className="flex items-center gap-2.5">
                  <PatientAvatar user={user} />
                  <div className="hidden leading-tight lg:block">
                    <p className="text-xs font-medium text-slate-800 light:text-app-text dark:text-slate-200">{user.full_name || 'Người dùng'}</p>
                    <p className="text-[10px] text-slate-500 light:text-app-secondary dark:text-slate-400">{user.role === 'staff' ? 'Bác sĩ / KTV' : 'Bệnh nhân'}</p>
                  </div>
                  <LogoutButton onClick={handleLogout} accountName={user.full_name || 'Tài khoản'} />
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link to="/register" className="text-xs font-medium text-slate-600 light:text-app-secondary dark:text-slate-300 hover:text-slate-900 light:hover:text-app-text dark:hover:text-white transition-colors px-2 py-1">
                    Đăng ký
                  </Link>
                  <Link
                    to="/login"
                    className="text-xs font-semibold text-white bg-blue-600 light:bg-app-primary hover:bg-blue-500 light:hover:bg-app-primary-hover px-3.5 py-1.5 rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>Đăng nhập</span>
                  </Link>
                </div>
              )}
            </div>

            {/* Menu toggle inspired by Uiverse.io / nathAd17 */}
            <button
              type="button"
              onClick={() => setMenuOpen(value => !value)}
              aria-label={menuOpen ? 'Thu gọn menu' : 'Mở rộng menu'}
              aria-expanded={menuOpen}
              aria-controls="desktop-navigation mobile-navigation"
              className="group relative isolate inline-flex shrink-0 items-center justify-center gap-2 overflow-hidden rounded-full border-2 border-emerald-100 bg-[#f6fcf9] px-3 py-1.5 text-xs font-semibold text-emerald-950 shadow-sm backdrop-blur-md transition-colors hover:text-[#f6fcf9] before:absolute before:-left-full before:-z-10 before:aspect-square before:w-full before:rounded-full before:bg-emerald-700 before:transition-all before:duration-700 hover:before:left-0 hover:before:scale-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 sm:px-4 sm:text-sm dark:border-emerald-800 dark:bg-[#10271e] dark:text-emerald-100 motion-reduce:before:transition-none"
            >
              <span>Menu</span>
              <svg
                aria-hidden="true"
                className={`h-7 w-7 rounded-full border border-emerald-800/50 p-1.5 transition-all duration-300 group-hover:border-transparent group-hover:bg-[#f6fcf9] group-hover:text-emerald-950 motion-reduce:transition-none ${menuOpen ? 'rotate-0 group-hover:rotate-45' : 'rotate-180 group-hover:rotate-[225deg]'}`}
                viewBox="0 0 16 19"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M7 18C7 18.5523 7.44772 19 8 19C8.55228 19 9 18.5523 9 18H7ZM8.70711 0.292893C8.31658 -0.0976311 7.68342 -0.0976311 7.29289 0.292893L0.928932 6.65685C0.538408 7.04738 0.538408 7.68054 0.928932 8.07107C1.31946 8.46159 1.95262 8.46159 2.34315 8.07107L8 2.41421L13.6569 8.07107C14.0474 8.46159 14.6805 8.46159 15.0711 8.07107C15.4616 7.68054 15.4616 7.04738 15.0711 6.65685L8.70711 0.292893ZM9 18L9 1H7L7 18H9Z"
                  fill="currentColor"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* ─── Navigation tabs (Desktop / Tablet horizontal scroll) ─────────────────────────── */}
      <div
        id="desktop-navigation"
        inert={!menuOpen}
        aria-hidden={!menuOpen}
        className={`hidden transition-[grid-template-rows] duration-300 motion-reduce:transition-none sm:grid ${menuOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
      >
        <div className="min-h-0 overflow-hidden">
        <div className="border-t border-emerald-100 bg-[#f6fcf9]/90 dark:border-slate-800/60 dark:bg-[#0B1329]/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-6 overflow-x-auto scrollbar-none">
          <nav className="flex shrink-0 items-center gap-3 px-1 py-2">
            {navItems.map(item => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                className="patient-nav-tab flex shrink-0 items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium sm:text-sm"
              >
                {item.icon && <item.icon className="w-3.5 h-3.5" />}
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 light:bg-app-primary dark:bg-cyan-400"></span>
            <span>Tiêu chuẩn ATS Cấp 1–5 • HIPAA Compliant</span>
          </div>
        </div>
      </div>

      </div>
      </div>

      {/* ─── Mobile Slide-down Drawer Menu ─────────────────────────── */}
      {menuOpen && (
        <div id="mobile-navigation" className="sm:hidden border-t border-slate-200 light:border-app-border dark:border-slate-800 bg-[#f6fcf9]/95 dark:bg-[#0B1329]/95 backdrop-blur-xl px-4 py-4 space-y-3 animate-fade-in shadow-2xl">
          {/* HITL Doctor Safety Badge on Mobile */}
          <div className="flex items-center justify-between p-2.5 rounded-xl border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 text-xs font-medium">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Bác Sĩ Trực Ban Lâm Sàng Giám Sát 24/7</span>
            </div>
            <span className="text-[10px] font-mono border border-emerald-400/40 px-1.5 py-0.5 rounded">HITL</span>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-3 px-1 py-2">
            {navItems.map(item => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                onClick={() => setMenuOpen(false)}
                className="patient-nav-tab flex items-center gap-3 px-3.5 py-2.5 text-sm font-medium"
              >
                {item.icon ? <item.icon className="w-4 h-4 shrink-0" /> : <div className="w-4 h-4 flex items-center justify-center font-bold text-xs">•</div>}
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="pt-2 border-t border-slate-200 light:border-app-border dark:border-slate-800/80 space-y-2">
            {user ? (
              <LogoutButton onClick={handleLogout} accountName={user.full_name || 'Tài khoản'} />
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Link
                  to="/register"
                  onClick={() => setMenuOpen(false)}
                  className="btn-clinical-ghost py-2 text-center text-xs font-medium flex items-center justify-center"
                >
                  Đăng ký
                </Link>
                <Link
                  to="/login"
                  onClick={() => setMenuOpen(false)}
                  className="btn-clinical-primary py-2 text-center text-xs font-semibold flex items-center justify-center gap-1.5"
                >
                  <User className="w-3.5 h-3.5" />
                  <span>Đăng nhập</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

