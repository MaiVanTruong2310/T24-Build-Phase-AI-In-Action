import { useState, useRef, useEffect } from 'react'
import { Bell, ChevronDown, Menu, UserRound, LogOut, Settings, User as UserIcon } from 'lucide-react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState, AppDispatch } from '../app/store'
import { logoutUser } from '../features/auth/authSlice'
import { BrandMark } from './BrandMark'
import { ChatbotWidget } from './ChatbotWidget'

const navItems = [
  { to: '/', label: 'Tổng quan' },
  { to: '/patient', label: 'Khu bệnh nhân' },
  { to: '/staff', label: 'Khu nhân viên' }
]

export function RootLayout() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  const { user } = useSelector((state: RootState) => state.auth)
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await dispatch(logoutUser())
    setIsDropdownOpen(false)
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <div className="flex items-center gap-2">
            <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Thông báo">
              <Bell className="size-5" />
            </button>
            
            {user ? (
              <div className="relative" ref={dropdownRef}>
                <button 
                  type="button" 
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="hidden items-center gap-2 rounded-lg p-2 text-left hover:bg-slate-100 sm:flex" 
                  aria-label="Tài khoản"
                >
                  <span className="grid size-8 place-items-center rounded-full bg-sky-100 text-sky-700">
                    <UserRound className="size-4" />
                  </span>
                  <span className="text-sm font-medium text-slate-700">{user.full_name || 'Tài khoản'}</span>
                  <ChevronDown className="size-4 text-slate-400" />
                </button>

                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-slate-100 py-2 z-50">
                    <div className="px-4 py-2 border-b border-slate-100 mb-2">
                      <p className="text-sm font-semibold text-slate-900 truncate">{user.full_name}</p>
                      <p className="text-xs text-slate-500 truncate">{user.email || user.phone}</p>
                    </div>
                    
                    <Link 
                      to="/profile" 
                      onClick={() => setIsDropdownOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-sky-600 transition-colors"
                    >
                      <UserIcon className="w-4 h-4" />
                      Hồ sơ cá nhân
                    </Link>
                    
                    <Link 
                      to="/settings" 
                      onClick={() => setIsDropdownOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-sky-600 transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      Cài đặt
                    </Link>
                    
                    <div className="border-t border-slate-100 my-2"></div>
                    
                    <button 
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors text-left"
                    >
                      <LogOut className="w-4 h-4" />
                      Đăng xuất
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link to="/login" className="hidden sm:flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white bg-sky-600 hover:bg-sky-700 transition-colors">
                Đăng nhập
              </Link>
            )}

            <button type="button" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 sm:hidden" aria-label="Mở menu">
              <Menu className="size-5" />
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 pb-3 sm:px-6 lg:px-8" aria-label="Điều hướng chính">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <ChatbotWidget />
    </div>
  )
}
