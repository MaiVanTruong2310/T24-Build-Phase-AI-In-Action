import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Search, Settings, ArrowRightLeft,
  LayoutDashboard, Activity, ListOrdered, MessageSquare, 
  CalendarCheck, Stethoscope, Briefcase, Users, 
  Building2, Package, ShieldAlert, LogOut, CalendarRange
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../app/store';
import { logoutUser } from '../features/auth/authSlice';
import { getUserAvatarUrl } from '../features/auth/session';
import { NotificationBell } from '../features/notification/NotificationBell';

export function StaffLayout() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { user } = useSelector((state: RootState) => state.auth);

  const handleLogout = async () => {
    await dispatch(logoutUser());
    navigate('/login');
  };

  const handleOpenPatientPortal = () => {
    // Keep the staff-to-patient portal switch explicit so it works from every
    // staff page, including pages rendered by nested routes.
    navigate('/patient');
  };

  const navItems = [
    { to: '/staff', label: 'Tổng quan quản trị', icon: LayoutDashboard, end: true },
    { to: '/staff/dieu-phoi', label: 'Điều phối khám', icon: Activity },
    { to: '/staff/queue', label: 'HITL Queue', icon: ListOrdered },
    { to: '/staff/chat', label: 'Chat Takeover', icon: MessageSquare },
    { to: '/staff/appointments', label: 'Duyệt lịch hẹn', icon: CalendarCheck },
    { to: '/staff/doctor-schedule', label: 'Quản Lý Lịch Bác Sĩ', icon: CalendarRange },
    { to: '/staff/doctors', label: 'Quản Lý Bác Sĩ', icon: Stethoscope },
    { to: '/staff/specialties', label: 'Quản lý chuyên khoa', icon: Briefcase },
    { to: '/staff/patients', label: 'Quản Lý Bệnh Nhân', icon: Users },
    { to: '/staff/facilities', label: 'Cơ sở bệnh viện', icon: Building2 },
    { to: '/staff/services', label: 'Gói dịch vụ y tế', icon: Package },
    { to: '/staff/monitoring', label: 'Xử lý Escalation', icon: ShieldAlert, alert: true },
  ];

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Top Header - Full Width */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between z-20 flex-shrink-0">
        <div className="flex items-center gap-8">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-xl leading-none">+</span>
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-sky-800 leading-none mb-1">VCare+</h1>
              <p className="text-[9px] uppercase font-bold text-slate-500 tracking-wider leading-none">Hệ Thống Quản Trị Y Tế</p>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative hidden md:block w-[300px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Tìm kiếm bác sĩ, chuyên khoa, phòng khám" 
              className="w-full pl-10 pr-4 py-2 bg-slate-100 border-transparent rounded-full text-sm focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 transition-all outline-none"
            />
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Actions & Profile */}
          <div className="flex items-center gap-4">
            <NotificationBell enabled={Boolean(user)} />
            <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors">
              <Settings size={20} />
            </button>
            
            {user ? (
              <div 
                className="flex items-center gap-3 pl-4 border-l border-slate-200 cursor-pointer hover:bg-slate-50 p-1.5 rounded-lg transition-colors group"
                onClick={handleLogout}
                title="Đăng xuất"
              >
                <img src={getUserAvatarUrl(user)} alt={user.full_name || 'Người dùng'} className="w-9 h-9 rounded-full object-cover border border-slate-200 group-hover:hidden" />
                <div className="w-9 h-9 rounded-full bg-red-100 text-red-600 hidden group-hover:flex items-center justify-center">
                  <LogOut className="w-4 h-4" />
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-bold text-slate-800">{user.full_name || 'Người dùng'}</p>
                  <p className="text-[10px] text-slate-500 font-semibold uppercase">Quản trị viên</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
                <div className="w-9 h-9 rounded-full bg-slate-200 animate-pulse"></div>
                <div className="hidden sm:block space-y-2">
                  <div className="h-3 w-24 bg-slate-200 rounded animate-pulse"></div>
                  <div className="h-2 w-16 bg-slate-200 rounded animate-pulse"></div>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Layout Area */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Sidebar Navigation */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between flex-shrink-0 overflow-y-auto">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => 
                  `flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                    isActive 
                      ? (item.alert ? 'bg-rose-50 text-rose-700' : 'bg-sky-50 text-sky-700') 
                      : (item.alert ? 'text-rose-600 hover:bg-rose-50' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50')
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <item.icon size={18} className={item.alert ? '' : 'opacity-70'} />
                  {item.label}
                </div>
              </NavLink>
            ))}
          </nav>

          {/* Sidebar Bottom Actions */}
          <div className="p-4 border-t border-slate-100 space-y-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-green-50/50 text-green-700 rounded-lg text-xs font-bold border border-green-100">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
              Hệ thống an toàn
            </div>
            <Link
              to="/patient"
              onClick={handleOpenPatientPortal}
              className="w-full flex items-center justify-center gap-2 text-sm font-semibold text-sky-700 hover:text-sky-800 hover:bg-sky-50 px-3 py-2.5 rounded-xl transition-colors border border-transparent hover:border-sky-100"
            >
              <ArrowRightLeft size={16} />
              Cổng Bệnh Nhân
            </Link>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 w-full relative z-0 overflow-y-auto bg-slate-50/50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
