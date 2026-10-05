import { Outlet, useLocation } from 'react-router-dom';
import { AuthDoodle } from '../components/AuthDoodle';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { ChatbotWidget } from './ChatbotWidget';

export function AuthLayout() {
  const { pathname } = useLocation();
  const doodleAuth = pathname === '/login' || pathname === '/register';
  return (
    <div className="min-h-screen bg-[#F8FAFC] light:bg-app-page dark:bg-[#0B1329] text-slate-900 light:text-app-text dark:text-slate-100 relative overflow-x-hidden flex flex-col font-sans transition-colors duration-300">
      {/* Ambient Medical Glow Orbs */}
      <div className="medical-glow-orb orb-clinical-blue top-1/4 right-0 w-[600px] h-[600px]" />
      <div className="medical-glow-orb orb-clinical-cyan bottom-10 left-10 w-[500px] h-[500px]" />

      <Header />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center relative z-10 p-4 py-12">
        <>{doodleAuth ? <AuthDoodle><Outlet /></AuthDoodle> : <Outlet />}</>
      </main>

      <Footer />
      <ChatbotWidget />
    </div>
  );
}
