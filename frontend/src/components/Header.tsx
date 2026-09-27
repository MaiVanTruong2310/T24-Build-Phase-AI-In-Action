import { memo } from 'react'
import { Link } from 'react-router-dom'
import { PlusSquare, Phone, User } from 'lucide-react'

export const Header = memo(function Header() {
  return (
    <header className="flex items-center justify-between px-8 py-4 relative z-10 bg-white">
      <div className="flex items-center gap-2">
        <div className="bg-sky-600 text-white p-1 rounded">
          <PlusSquare className="w-6 h-6" strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900 leading-tight">MediCare AI</h1>
          <p className="text-xs text-slate-500 font-medium tracking-wide">Clinical Intelligence System</p>
        </div>
      </div>
      
      <div className="flex items-center gap-6">
        <Link to="/" className="text-sm font-medium text-slate-600 hover:text-sky-600 transition-colors">
          Về trang chủ
        </Link>
        <div className="flex items-center gap-2 text-sky-600 font-semibold text-sm">
          <Phone className="w-4 h-4" />
          <span>Hotline: 1900 6868</span>
        </div>
        <button className="bg-sky-700 text-white p-2 rounded-full hover:bg-sky-800 transition-colors">
          <User className="w-5 h-5" />
        </button>
      </div>
    </header>
  )
})
