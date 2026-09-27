import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Lock, ArrowRight, Loader2 } from 'lucide-react'

export function ForgotPassword() {
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    // Simulate API call
    setTimeout(() => {
      setLoading(false)
    }, 1500)
  }

  return (
    <div className="w-full max-w-md">
      <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8 text-center">
        <div className="w-16 h-16 bg-sky-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Lock className="w-8 h-8 text-sky-600" />
        </div>
        
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Khôi phục mật khẩu</h2>
        <p className="text-sm text-slate-500 mb-8 leading-relaxed">
          Vui lòng nhập số điện thoại hoặc email đã đăng ký. Chúng tôi sẽ gửi mã xác thực (OTP) để bạn đặt lại mật khẩu mới.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-1.5 text-left">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="email">
              Số điện thoại hoặc Email
            </label>
            <input
              id="email"
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Nhập thông tin"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm placeholder:text-slate-400 bg-white"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Gửi mã xác thực
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-sm">
          <Link to="/login" className="font-semibold text-sky-600 hover:text-sky-700">
            Quay lại đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
