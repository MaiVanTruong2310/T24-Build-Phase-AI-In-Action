import { Outlet, useLocation } from 'react-router-dom'
import { ChatbotWidget } from './ChatbotWidget'
import { Header } from '../pages/Landing/Header'
import { Footer } from '../pages/Landing/Footer'

export function RootLayout() {
  const { pathname } = useLocation()
  const hasEmbeddedAgent = pathname === '/patient' || pathname === '/patient/'

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B1329] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-300">
      <Header />
      <main className="flex-1 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 w-full">
        <Outlet />
      </main>
      <Footer />
      {!hasEmbeddedAgent && <ChatbotWidget />}
    </div>
  )
}


