import { Outlet } from 'react-router-dom'
import { ChatbotWidget } from './ChatbotWidget'
import { Header } from '../pages/Landing/Header'

export function RootLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <ChatbotWidget />
    </div>
  )
}
