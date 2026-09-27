import { memo } from 'react'
import { ShieldCheck, Lock } from 'lucide-react'

export const Footer = memo(function Footer() {
  return (
    <footer className="px-8 py-6 flex items-center justify-between text-xs text-slate-500 border-t border-slate-200 relative z-10 bg-white/50 backdrop-blur-md mt-auto">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          HIPAA Compliant
        </div>
        <span className="w-1 h-1 rounded-full bg-slate-300"></span>
        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
          <Lock className="w-4 h-4 text-emerald-600" />
          ISO 27001 Certified
        </div>
        <span className="w-1 h-1 rounded-full bg-slate-300"></span>
        <span>© 2024 MediCare AI. All rights reserved.</span>
      </div>
      
      <div className="flex items-center gap-6">
        <a href="#" className="hover:text-slate-800 transition-colors">Điều khoản sử dụng</a>
        <a href="#" className="hover:text-slate-800 transition-colors">Chính sách bảo mật</a>
      </div>
    </footer>
  )
})
