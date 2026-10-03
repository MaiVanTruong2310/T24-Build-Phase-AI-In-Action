import { memo } from 'react'
import { ShieldCheck, Lock } from 'lucide-react'

export const Footer = memo(function Footer() {
  return (
    <footer className="px-6 sm:px-8 py-5 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 relative z-10 bg-[#070D1E]/90 backdrop-blur-md mt-auto w-full gap-3">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5 text-slate-300 font-medium">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>HIPAA Compliant</span>
        </div>
        <span className="w-1 h-1 rounded-full bg-slate-600 hidden sm:inline-block"></span>
        <div className="flex items-center gap-1.5 text-slate-300 font-medium">
          <Lock className="w-4 h-4 text-cyan-400" />
          <span>ISO 27001 Certified</span>
        </div>
        <span className="w-1 h-1 rounded-full bg-slate-600 hidden sm:inline-block"></span>
        <span>© 2026 VCare+ Health System.</span>
      </div>
      
      <div className="flex items-center gap-5">
        <a href="#" className="hover:text-slate-200 transition-colors">Điều khoản dịch vụ</a>
        <a href="#" className="hover:text-slate-200 transition-colors">Bảo mật bệnh án</a>
      </div>
    </footer>
  )
})
