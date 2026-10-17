import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileText,
  LogOut,
  Menu,
  MessageCircle,
  Phone,
  ShieldCheck,
  X,
} from 'lucide-react'
import type { AppDispatch, RootState } from '../../app/store'
import { logoutUser } from '../../features/auth/authSlice'
import { PatientAvatar } from '../../components/PatientAvatar'
import { NotificationBell } from '../../features/notification/NotificationBell'
import { ThemeToggle } from '../../components/ThemeToggle'
import { SimpleModeToggle } from '../../components/SimpleModeToggle'
import { Visible } from '../../features/uiVisibility/Visible'
import { uiPreviewRole } from '../../features/uiVisibility/store'
import type { UiKey } from '../../features/uiVisibility/registry'
import './Header.css'
import { SosButton } from '../../features/chat/SosButton'

type NavItem = { label: string; to: string; end?: boolean }

// Chỉ hiện mục mà vai trò hiện tại dùng được: khách chỉ thấy trang công khai,
// các trang cần đăng nhập (tiến trình, hồ sơ, lịch sử...) chỉ hiện sau khi đăng nhập.
function navItemsFor(role: 'patient' | 'staff' | undefined): NavItem[] {
  if (role === 'patient') {
    return [
      { label: 'Tư vấn AI', to: '/patient', end: true },
      { label: 'Tìm bác sĩ', to: '/patient/doctors' },
      { label: 'Tiến trình điều trị', to: '/patient/progress' },
    ]
  }
  if (role === 'staff') return [{ label: 'Bảng điều phối', to: '/staff' }]
  return [
    { label: 'Trang chủ', to: '/', end: true },
    { label: 'Tìm bác sĩ', to: '/patient/doctors' },
    { label: 'Đặt lịch', to: '/patient/appointments' },
  ]
}

// Mục menu → khoá ẩn/hiện (/staff/ui-editor). Mục của nhân viên không có khoá.
const NAV_KEYS: Record<string, UiKey> = {
  '/': 'header.nav.home',
  '/patient': 'header.nav.consult',
  '/patient/doctors': 'header.nav.doctors',
  '/patient/appointments': 'header.nav.booking',
  '/patient/progress': 'header.nav.progress',
}

const ACCOUNT_LINKS = [
  { label: 'Hồ sơ bệnh án', to: '/patient/profile', icon: FileText },
]

function DoodleBrand() {
  return (
    <Link to="/" className="hd-brand" aria-label="VCare+ · Trang chủ">
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path d="M18 10h20v16h16v18H38v16H18V44H4V26h14z" fill="var(--app-accent)" />
        <path d="M23 5l18 1 1 17 17-1-1 19-15 1-1 17-21-1 1-15-17-1 1-21 15 1z" fill="none" stroke="var(--hd-ink)" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
        <path d="M22 6.5l19.5-.5-.5 17.5 17 .5-.5 18-16.5.5.5 17-19 .5-.5-16.5-16-.5.5-19 16 .5z" fill="none" stroke="var(--hd-ink)" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <span className="hd-wordmark">VCare<span>+</span></span>
    </Link>
  )
}

function NavTags({ items, row = false, onNavigate }: { items: NavItem[]; row?: boolean; onNavigate?: () => void }) {
  const className = `hd-tag${row ? ' hd-tag--row' : ''}`
  return (
    <>
      {items.map((item) => {
        const content = (
          <>
            {item.label}
            {row && <ChevronRight className="h-[18px] w-[18px]" strokeWidth={2.4} aria-hidden="true" />}
          </>
        )
        const link = <NavLink key={item.label} to={item.to} end={item.end} className={className} onClick={onNavigate}>{content}</NavLink>
        const key = NAV_KEYS[item.to]
        return key ? <Visible key={item.label} id={key} inline>{link}</Visible> : link
      })}
    </>
  )
}

export function Header() {
  const dispatch = useDispatch<AppDispatch>()
  const { pathname } = useLocation()
  const signedInUser = useSelector((state: RootState) => state.auth.user)
  // Trang admin xem trước giao diện như khách / bệnh nhân (admin đăng nhập bằng tài khoản nhân viên).
  const previewRole = uiPreviewRole()
  const user = previewRole === 'guest' ? null : signedInUser
  const [accountOpen, setAccountOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const headerRef = useRef<HTMLElement>(null)
  const accountRef = useRef<HTMLDivElement>(null)
  const accountButtonRef = useRef<HTMLButtonElement>(null)

  const role = previewRole === 'patient' ? 'patient' : user?.role
  const navItems = navItemsFor(role)
  const roleLabel = role === 'staff' ? 'Bác sĩ / KTV' : 'Bệnh nhân'
  const cta: { label: string; to: string; icon: ReactNode } | null =
    role === 'patient'
      ? { label: 'Đặt lịch khám', to: '/patient/appointments', icon: <Calendar className="h-[17px] w-[17px]" strokeWidth={2.2} aria-hidden="true" /> }
      : role === 'staff'
        ? null
        : { label: 'Tư vấn ngay', to: '/patient', icon: <MessageCircle className="h-[17px] w-[17px]" strokeWidth={2.2} aria-hidden="true" /> }

  // Đổi trang thì đóng menu.
  useEffect(() => {
    setAccountOpen(false)
    setDrawerOpen(false)
  }, [pathname])

  // Menu tài khoản: bấm ra ngoài hoặc nhấn Escape thì đóng (Escape trả focus về nút).
  useEffect(() => {
    if (!accountOpen && !drawerOpen) return undefined
    const onPointerDown = (event: MouseEvent) => {
      if (accountOpen && accountRef.current && !accountRef.current.contains(event.target as Node)) setAccountOpen(false)
      if (drawerOpen && headerRef.current && !headerRef.current.contains(event.target as Node)) setDrawerOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      if (accountOpen) accountButtonRef.current?.focus()
      setAccountOpen(false)
      setDrawerOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [accountOpen, drawerOpen])

  const handleLogout = () => {
    dispatch(logoutUser())
    setAccountOpen(false)
    setDrawerOpen(false)
  }

  const closeDrawer = () => setDrawerOpen(false)

  return (
    <header className="hd" ref={headerRef}>
      <div className="hd-row mx-auto flex h-[68px] max-w-7xl items-center gap-2.5 px-4 sm:px-6 xl:h-[76px] xl:max-w-[1536px] xl:gap-9">
        <Visible id="header.brand" inline><DoodleBrand /></Visible>

        {/* Desktop: các tag nằm trên một sợi chỉ khâu */}
        <nav aria-label="Điều hướng chính" className="hd-nav hidden flex-1 xl:flex">
          <span className="hd-thread" aria-hidden="true" />
          <span className="hd-knot hd-knot--start" aria-hidden="true" />
          <span className="hd-knot hd-knot--end" aria-hidden="true" />
          <NavTags items={navItems} />
        </nav>

        <div className="hd-actions ml-auto flex items-center gap-2.5 xl:gap-3.5">
          <Visible id="header.sos" inline>
            <SosButton className="hd-sos">
              <Phone className="h-[17px] w-[17px]" strokeWidth={2.2} aria-hidden="true" />
              <span className="hd-sos__label">Cấp cứu</span>
              <b>115</b>
            </SosButton>
          </Visible>

          <Visible id="header.notifications" inline><NotificationBell enabled={Boolean(user)} /></Visible>

          {/* Bọc div: .simple-toggle đặt display trong CSS thường nên đè class `hidden` của Tailwind */}
          <Visible id="header.simple_toggle" inline>
            <div className="hidden xl:block">
              <SimpleModeToggle />
            </div>
          </Visible>
          <Visible id="header.theme_toggle" inline>
            <div className="hidden xl:block">
              <ThemeToggle />
            </div>
          </Visible>

          {!user && <Visible id="header.login" inline><Link to="/login" className="hd-login hidden xl:inline-flex">Đăng nhập</Link></Visible>}
          {cta && (
            <Visible id="header.cta" inline>
              <Link to={cta.to} className="hd-cta hidden xl:inline-flex">
                {cta.icon}
                <span>{cta.label}</span>
              </Link>
            </Visible>
          )}

          {user ? (
            <>
              {/* Desktop: menu tài khoản dạng bong bóng thoại */}
              <div className="relative hidden xl:block" ref={accountRef}>
                <button
                  ref={accountButtonRef}
                  type="button"
                  className="hd-avatar-btn"
                  aria-expanded={accountOpen}
                  aria-controls="account-panel"
                  aria-label={`Menu tài khoản ${user.full_name || ''}`.trim()}
                  onClick={() => setAccountOpen((value) => !value)}
                >
                  <PatientAvatar user={user} variant="round" />
                  {accountOpen ? <ChevronUp className="h-4 w-4" strokeWidth={2.4} aria-hidden="true" /> : <ChevronDown className="h-4 w-4" strokeWidth={2.4} aria-hidden="true" />}
                </button>

                {accountOpen && (
                  <div id="account-panel" className="hd-bubble">
                    <div className="flex items-center gap-3 px-2 pb-3 pt-2">
                      <PatientAvatar user={user} variant="round-lg" />
                      <div className="min-w-0">
                        <p className="truncate text-[15px] font-bold text-app-text">{user.full_name || 'Người dùng'}</p>
                        {user.email && <p className="truncate text-xs text-app-secondary">{user.email}</p>}
                      </div>
                      <span className="hd-chip">{roleLabel}</span>
                    </div>
                    {role === 'patient' && (
                      <div>
                        {ACCOUNT_LINKS.map(({ label, to, icon: Icon }) => (
                          <Link key={to} to={to} className="hd-item">
                            <Icon className="h-[19px] w-[19px]" strokeWidth={2.1} aria-hidden="true" />
                            <span>{label}</span>
                          </Link>
                        ))}
                      </div>
                    )}
                    <div className="hd-divider" aria-hidden="true" />
                    <button type="button" className="hd-item hd-item--danger" onClick={handleLogout}>
                      <LogOut className="h-[19px] w-[19px]" strokeWidth={2.2} aria-hidden="true" />
                      <span>Đăng xuất</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Mobile / tablet: avatar mở ngăn kéo */}
              <button
                type="button"
                className="hd-avatar-btn hd-avatar-btn--round xl:hidden"
                aria-expanded={drawerOpen}
                aria-controls="mobile-drawer"
                aria-label={drawerOpen ? 'Đóng menu tài khoản' : 'Mở menu tài khoản'}
                onClick={() => setDrawerOpen((value) => !value)}
              >
                <PatientAvatar user={user} variant="round" />
              </button>
            </>
          ) : (
            <button
              type="button"
              className="hd-iconbtn xl:hidden"
              aria-expanded={drawerOpen}
              aria-controls="mobile-drawer"
              aria-label={drawerOpen ? 'Đóng menu' : 'Mở menu'}
              onClick={() => setDrawerOpen((value) => !value)}
            >
              {drawerOpen ? <X className="h-5 w-5" strokeWidth={2.6} aria-hidden="true" /> : <Menu className="h-5 w-5" strokeWidth={2.6} aria-hidden="true" />}
            </button>
          )}
        </div>
      </div>

      {/* Nét mực gợn sóng thay cho đường kẻ thẳng */}
      <svg className="hd__wave" aria-hidden="true" viewBox="0 0 1440 10" preserveAspectRatio="none">
        <path
          d="M0 5 C 120 2, 200 8, 340 4 S 560 1, 700 5 S 940 8, 1080 4 S 1320 2, 1440 5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* Ngăn kéo cho màn hình dưới 1280px */}
      {drawerOpen && (
        <div id="mobile-drawer" className="hd-drawer xl:hidden">
          {user && (
            <div className="flex items-center gap-3 px-1">
              <PatientAvatar user={user} variant="round-lg" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-base font-bold text-app-text">{user.full_name || 'Người dùng'}</p>
                {user.email && <p className="truncate text-xs text-app-secondary">{user.email}</p>}
              </div>
              <span className="hd-chip">{roleLabel}</span>
            </div>
          )}

          <nav aria-label="Điều hướng chính" className={`hd-drawer-nav ${user ? 'mt-7' : 'mt-3'}`}>
            <NavTags items={navItems} row onNavigate={closeDrawer} />
          </nav>

          {cta && (
            <Link to={cta.to} className="hd-cta hd-cta--block mt-6" onClick={closeDrawer}>
              {cta.icon}
              <span>{cta.label}</span>
            </Link>
          )}

          {!user && (
            <div className="mt-3.5 grid grid-cols-2 gap-3.5">
              <Link to="/login" className="hd-btn" onClick={closeDrawer}>Đăng nhập</Link>
              <Link to="/register" className="hd-btn" onClick={closeDrawer}>Đăng ký</Link>
            </div>
          )}

          {role === 'patient' && (
            <div className="mt-5 grid grid-cols-2 gap-2.5">
              {ACCOUNT_LINKS.map(({ label, to, icon: Icon }) => (
                <Link key={to} to={to} className="hd-tile" onClick={closeDrawer}>
                  <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2.1} aria-hidden="true" />
                  <span>{label}</span>
                </Link>
              ))}
            </div>
          )}

          <div className="mt-auto flex flex-col gap-3 pt-6">
            {!user && (
              <div className="hd-note">
                <ShieldCheck className="h-[22px] w-[22px] shrink-0" strokeWidth={2.1} aria-hidden="true" />
                <span>Bác sĩ trực ban giám sát mọi kết quả sàng lọc, 24/7</span>
              </div>
            )}
            <div className="flex min-h-[50px] items-center justify-between rounded-xl border-2 border-[var(--hd-ink)] bg-[var(--hd-paper)] px-4 text-[15px] font-semibold text-app-text shadow-[2px_2px_0_var(--hd-shadow)]">
              <span>Giao diện</span>
              <ThemeToggle />
            </div>
            <SimpleModeToggle className="min-h-[50px] w-full justify-start px-4 text-[15px]" />
            {user && (
              <button type="button" className="hd-btn hd-btn--danger" onClick={handleLogout}>
                <LogOut className="h-[17px] w-[17px]" strokeWidth={2.3} aria-hidden="true" />
                <span>Đăng xuất</span>
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
