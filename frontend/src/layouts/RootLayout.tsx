import { lazy, Suspense, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
const ChatbotWidget = lazy(() => import('./ChatbotWidget').then((module) => ({ default: module.ChatbotWidget })))
import { TypewriterLoader } from '../components/TypewriterLoader'
import { Header } from '../pages/Landing/Header'
import { Footer } from '../pages/Landing/Footer'
import { ZaloBotButton } from '../components/ZaloBotButton'
import { Visible } from '../features/uiVisibility/Visible'

// Tải trước code các tab bệnh nhân hay dùng khi trình duyệt rảnh, để lần đầu đổi tab không phải chờ tải chunk.
const PREFETCH_TABS = [
  () => import('../pages/PatientConsultation'),
  () => import('../pages/DoctorDirectory'),
  () => import('../pages/AppointmentProgress'),
  () => import('../pages/ConsultationBooking'),
  () => import('../pages/PatientDepartments'),
]

export function RootLayout() {
  const { pathname } = useLocation()

  useEffect(() => {
    const prefetch = () => PREFETCH_TABS.forEach((load) => void load().catch(() => undefined))
    if (typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(prefetch, { timeout: 3000 })
      return () => window.cancelIdleCallback(id)
    }
    const timer = setTimeout(prefetch, 1500)
    return () => clearTimeout(timer)
  }, [])
  const hasEmbeddedAgent = pathname === '/patient' || pathname === '/patient/'
  const hasBookingForm = pathname === '/patient/appointments' || pathname === '/patient/appointments/'

  return (
    <div className={`bg-app-page light:bg-app-page dark:bg-app-page text-slate-900 light:text-app-text dark:text-slate-100 flex flex-col font-sans transition-colors duration-300 ${hasEmbeddedAgent ? 'chat-page-bg h-dvh overflow-hidden' : 'min-h-screen'}`}>
      <Header />
      <main className={hasEmbeddedAgent ? 'flex-1 min-h-0 w-full mx-auto max-w-[1100px] xl:max-w-[1380px] sm:px-6 sm:py-4' : 'flex-1 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 w-full'}>
        {/* Suspense riêng cho phần nội dung: đổi tab chỉ tải lại phần thân, header/footer giữ nguyên. */}
        <Suspense fallback={<div className="flex min-h-[50vh] items-center justify-center" role="status" aria-label="Đang tải trang"><TypewriterLoader size="lg" /></div>}>
          <Outlet />
        </Suspense>
      </main>
      {!hasEmbeddedAgent && <Visible id="global.footer"><Footer /></Visible>}
      {!hasEmbeddedAgent && !hasBookingForm && <Visible id="global.floating_chat"><Suspense fallback={null}><ChatbotWidget /></Suspense></Visible>}
      <Visible id="global.zalo_button"><ZaloBotButton lifted={hasEmbeddedAgent} /></Visible>
    </div>
  )
}
