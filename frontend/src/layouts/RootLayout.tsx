import { lazy, Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
const ChatbotWidget = lazy(() => import('./ChatbotWidget').then((module) => ({ default: module.ChatbotWidget })))
import { Header } from '../pages/Landing/Header'
import { Footer } from '../pages/Landing/Footer'

export function RootLayout() {
  const { pathname } = useLocation()
  const hasEmbeddedAgent = pathname === '/patient' || pathname === '/patient/'
  const hasBookingForm = pathname === '/patient/appointments' || pathname === '/patient/appointments/'

  return (
    <div className="min-h-screen bg-[#F8FAFC] light:bg-app-page dark:bg-[#0B1329] text-slate-900 light:text-app-text dark:text-slate-100 flex flex-col font-sans transition-colors duration-300">
      <Header />
      <main className={`flex-1 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 w-full ${hasEmbeddedAgent ? '!py-3 sm:!py-8' : ''}`}>
        <Outlet />
      </main>
      <Footer />
      {!hasEmbeddedAgent && !hasBookingForm && <Suspense fallback={null}><ChatbotWidget /></Suspense>}
    </div>
  )
}
