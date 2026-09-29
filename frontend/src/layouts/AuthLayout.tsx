import { Outlet } from 'react-router-dom'
import { Header } from '../components/Header'
import { Footer } from '../components/Footer'
import { AIAssistantButton } from '../components/AIAssistantButton'

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-slate-50 relative overflow-x-hidden flex flex-col font-sans">
      {/* Background Gradient Orbs */}
      <div className="absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/4 w-[800px] h-[800px] bg-cyan-100/50 rounded-full blur-3xl -z-10" />

      <Header />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center relative z-10 p-4 py-12">
        <Outlet />
      </main>

      <Footer />
      <AIAssistantButton />
    </div>
  )
}
