import { LogoutButton } from '../components/LogoutButton';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { 
  Search, Bell, Settings, Flame, ArrowRightLeft, 
  LayoutDashboard, Activity, ListOrdered, MessageSquare, 
  CalendarCheck, Stethoscope, Briefcase, Users, 
  Building2, Package, ShieldAlert, CalendarRange
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../app/store';
import { logoutUser } from '../features/auth/authSlice';
import { getUserAvatarUrl } from '../features/auth/session';

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
    { to: '/staff/queue', label: 'HITL Queue', icon: ListOrdered, badge: 28 },
    { to: '/staff/chat', label: 'Chat Takeover', icon: MessageSquare, badge: 4 },
    { to: '/staff/appointments', label: 'Duyệt lịch hẹn', icon: CalendarCheck, badge: 12 },
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
          {/* Status Badges */}
          <div className="hidden xl:flex items-center gap-3 border-r border-slate-200 pr-6">
            <div className="text-right">
              <p className="text-[10px] text-slate-500 font-semibold uppercase">Công suất phòng</p>
              <p className="text-sm font-bold text-slate-800">86% <span className="text-xs text-slate-500 font-normal">(412/480)</span></p>
            </div>
            <div className="text-right pl-3 border-l border-slate-100">
              <p className="text-[10px] text-slate-500 font-semibold uppercase">Bác sĩ trực</p>
              <p className="text-sm font-bold text-sky-600">64 Đang online</p>
            </div>
            
            <div className="flex items-center gap-2 ml-4">
              <span className="px-3 py-1 bg-teal-50 text-teal-700 text-xs font-bold rounded-full flex items-center gap-1.5 border border-teal-100">
                <div className="w-1.5 h-1.5 bg-teal-500 rounded-full"></div>
                Đang trực ban
              </span>
              <span className="px-3 py-1 bg-rose-50 text-rose-700 text-xs font-bold rounded-full flex items-center gap-1.5 border border-rose-100 shadow-sm">
                <Flame size={14} className="text-rose-600" />
                2 Cấp cứu
              </span>
            </div>
          </div>

          {/* Actions & Profile */}
          <div className="flex items-center gap-4">
            <button className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full border-2 border-white shadow-sm">3</span>
            </button>
            <button className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors">
              <Settings size={20} />
            </button>
            
            {user ? (
              <div className="flex items-center gap-3 border-l border-slate-200 pl-4">
                <img src={getUserAvatarUrl(user)} alt={user.full_name || 'Người dùng'} className="h-9 w-9 rounded-full border border-slate-200 object-cover" />
                <div className="hidden sm:block">
                  <p className="text-sm font-bold text-slate-800">{user.full_name || 'Người dùng'}</p>
                  <p className="text-[10px] font-semibold uppercase text-slate-500">Quản trị viên</p>
                </div>
                <LogoutButton onClick={handleLogout} accountName={user.full_name || 'Tài khoản'} />
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
                {item.badge && (
                  <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                    item.alert ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {item.badge}
                  </span>
                )}
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
