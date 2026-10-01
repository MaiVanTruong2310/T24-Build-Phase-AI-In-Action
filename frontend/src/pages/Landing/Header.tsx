import React, { useState } from 'react';

import {
  ArrowRightLeft,
  Calendar,
  Clock,
  FileText,
  LogOut,
  Menu,
  MessageSquare,
  ShieldCheck,
  Stethoscope,
  User,
  X,
} from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../../app/store';
import { logoutUser } from '../../features/auth/authSlice';
import { getUserAvatarUrl } from '../../features/auth/session';
import { NotificationBell } from '../../features/notification/NotificationBell';
import { ThemeToggle } from '../../components/ThemeToggle';

export function Header() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    dispatch(logoutUser());
    setMobileMenuOpen(false);
  };

  const navItems = [
    { to: '/', label: 'Trang Chủ', end: true, icon: null },
    { to: '/patient', label: 'Tư Vấn AI & Bác Sĩ', end: true, icon: MessageSquare },
    { to: '/patient/appointments', label: 'Đặt Lịch Khám', end: true, icon: Calendar },
    { to: '/patient/progress', label: 'Tiến Trình Điều Trị', end: false, icon: Clock },
    { to: '/patient/profile', label: 'Hồ Sơ Bệnh Án', end: false, icon: FileText }
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#F8FAFC]/90 dark:bg-[#0B1329]/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800/80 transition-colors duration-300">
      {/* ─── Top bar ────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4 sm:gap-8">
          <Link to="/" className="flex items-center gap-2.5 sm:gap-3 transition-opacity hover:opacity-90">
            <img
              src="/vcare-logo.png"
              alt="VCare+ Logo"
              className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl object-contain bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-700 shadow-xs shrink-0 p-0.5"
            />
            <div className="leading-tight">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 tracking-tight">VCare+</span>
                <span className="font-mono text-[9px] sm:text-[10px] text-blue-700 dark:text-cyan-400 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-1.5 py-0.5 rounded">
                  CLINICAL
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-slate-500 dark:text-slate-400 font-medium truncate max-w-[170px] sm:max-w-none">
                Hệ Thống Y Tế Bác Sĩ Giám Sát
              </p>
            </div>
          </Link>

          <div className="hidden lg:flex items-center bg-slate-200/60 dark:bg-slate-900/60 rounded-xl border border-slate-300/70 dark:border-slate-800 p-1">
            <button className="px-3.5 py-1.5 bg-white dark:bg-blue-600/20 text-blue-700 dark:text-cyan-300 text-xs font-semibold rounded-lg shadow-xs dark:shadow-none border border-slate-200 dark:border-blue-500/30 transition-all">
              Cổng Bệnh Nhân
            </button>
            <Link
              to="/staff/queue"
              className="px-3.5 py-1.5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 text-xs font-medium transition-colors flex items-center gap-1.5"
            >
              <ArrowRightLeft className="w-3 h-3 text-slate-400" />
              <span>Bác Sĩ Điều Phối</span>
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:border-l border-slate-200 sm:pl-4">
          <NotificationBell enabled={Boolean(user)} />
          <div className="flex items-center gap-2 sm:gap-3">
            {/* HITL Doctor Safety Badge (Desktop & Tablet) */}
            <div className="hidden md:flex items-center gap-2 border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 px-3 py-1 text-xs font-medium rounded-xl">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />

            </div>

            {/* Theme Toggle Button (Light / Dark) */}
            <ThemeToggle />

            {/* User profile (Desktop) */}
            <div className="hidden sm:flex items-center gap-3 sm:border-l border-slate-200 dark:border-slate-800 sm:pl-3">
              {user ? (
                <div
                  className="flex items-center gap-2.5 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-800/60 p-1.5 rounded-xl transition-all group"
                  onClick={handleLogout}
                  title="Đăng xuất"
                >
                  <img
                    src={getUserAvatarUrl(user)}
                    alt={user.full_name}
                    className="w-8 h-8 rounded-lg border border-slate-300 dark:border-slate-700 group-hover:hidden object-cover"
                  />
                  <div className="w-8 h-8 rounded-lg bg-rose-100 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-500/30 text-rose-600 dark:text-rose-400 hidden group-hover:flex items-center justify-center">
                    <LogOut className="w-4 h-4" />
                  </div>
                  <div className="leading-tight hidden md:block">
                    <p className="text-xs font-medium text-slate-800 dark:text-slate-200">{user.full_name || 'Người dùng'}</p>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400">{user.role === 'staff' ? 'Bác sĩ / KTV' : 'Bệnh nhân'}</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link to="/register" className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors px-2 py-1">
                    Đăng ký
                  </Link>
                  <Link
                    to="/login"
                    className="text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 px-3.5 py-1.5 rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>Đăng nhập</span>
                  </Link>
                </div>
              )}
            </div>

            {/* Mobile Hamburger Toggle Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="sm:hidden p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Navigation tabs (Desktop / Tablet horizontal scroll) ─────────────────────────── */}
      <div className="hidden sm:block border-t border-slate-200/80 dark:border-slate-800/60 bg-[#F1F5F9]/70 dark:bg-[#0B1329]/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-12 flex items-center justify-between overflow-x-auto scrollbar-none">
          <nav className="flex items-center gap-1.5 shrink-0">
            {navItems.map(item => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `text-xs sm:text-sm font-medium px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shrink-0 transition-all ${isActive
                    ? 'bg-blue-600/10 dark:bg-blue-600/20 text-blue-700 dark:text-cyan-300 border border-blue-500/30'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/40'
                  }`}
              >
                {item.icon && <item.icon className="w-3.5 h-3.5" />}
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-cyan-400"></span>
            <span>Tiêu chuẩn ATS Cấp 1–5 • HIPAA Compliant</span>
          </div>
        </div>
      </div>

      {/* ─── Mobile Slide-down Drawer Menu ─────────────────────────── */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0B1329]/95 backdrop-blur-xl px-4 py-4 space-y-3 animate-fade-in shadow-2xl">
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
          <nav className="space-y-1">
            {navItems.map(item => (
              <NavLink
                key={item.label}
                to={item.to}
                end={item.end}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
              >
                {item.icon ? <item.icon className="w-4 h-4 shrink-0" /> : <div className="w-4 h-4 flex items-center justify-center font-bold text-xs">•</div>}
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 space-y-2">
            <Link
              to="/staff/queue"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-blue-700 dark:text-cyan-400 bg-blue-50 dark:bg-slate-900/60 border border-blue-200 dark:border-slate-800"
            >
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-3.5 h-3.5" />
                <span>Cổng Bác Sĩ Điều Phối</span>
              </div>
              <span className="text-[10px] uppercase font-mono">Staff</span>
            </Link>

            {user ? (
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30"
              >
                <LogOut className="w-4 h-4" />
                <span>Đăng xuất ({user.full_name || 'Tài khoản'})</span>
              </button>
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="btn-clinical-ghost py-2 text-center text-xs font-medium flex items-center justify-center"
                >
                  Đăng ký
                </Link>
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
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

