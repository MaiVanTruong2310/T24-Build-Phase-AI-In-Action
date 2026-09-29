import { useState, FormEvent, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { AppDispatch, RootState } from '../app/store'
import { loginUser } from '../features/auth/authSlice'
import { 
  Eye, 
  EyeOff, 
  ShieldCheck, 
  User, 
  ArrowRight,
  Loader2,
  Lock,
  MessageSquare
} from 'lucide-react'

export function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  
  const { loading, error, user } = useSelector((state: RootState) => state.auth)

  const [validationError, setValidationError] = useState('')

  useEffect(() => {
    if (user) {
      if (user.role === 'staff') {
        navigate('/staff')
      } else {
        navigate('/patient')
      }
    }
  }, [user, navigate])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')

    if (username.length < 7) {
      setValidationError('Tên đăng nhập (Email/SĐT) quá ngắn.')
      return
    }

    if (password.length < 8 || password.length > 128) {
      setValidationError('Mật khẩu phải có độ dài từ 8 đến 128 ký tự.')
      return
    }

    await dispatch(loginUser({ username, password }))
  }

  return (
    <div className="w-full max-w-md">
      <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
        {/* Form Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-full text-xs font-semibold">
            <ShieldCheck className="w-4 h-4" />
            Cổng bảo mật y tế số
          </div>
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            Sẵn sàng kết nối AI
          </div>
        </div>

        <h2 className="text-2xl font-bold text-slate-900 mb-2">Đăng nhập MediCare AI</h2>
        <p className="text-sm text-slate-500 mb-8 leading-relaxed">
          Chào mừng bạn quay lại. Vui lòng đăng nhập để tiếp tục chăm sóc sức khỏe.
        </p>

        {(error || validationError) && (
          <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600 flex items-start gap-2">
            <div className="mt-0.5">⚠️</div>
            <p>{validationError || error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="username">
              Số điện thoại, Email hoặc Số CCCD
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="0912 345 678 hoặc 00120100xxxx"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm placeholder:text-slate-400 bg-white"
              disabled={loading}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="password">
              Mật khẩu
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm placeholder:text-slate-400 bg-white"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded text-sky-600 focus:ring-sky-500/20" />
              <span className="text-sm font-medium text-slate-600">Ghi nhớ đăng nhập</span>
            </label>
            <Link to="/forgot-password" className="text-sm font-semibold text-sky-600 hover:text-sky-700 transition-colors">
              Quên mật khẩu?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Đang xử lý...
              </>
            ) : (
              <>
                Đăng nhập
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8">
          <div className="relative flex items-center justify-center mb-6">
            <div className="absolute border-t border-slate-200 w-full"></div>
            <span className="bg-white px-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">
              Hoặc đăng nhập bằng
            </span>
          </div>

          <div className="space-y-3">
            <button className="w-full flex items-center justify-between px-4 py-3 border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-red-50 flex items-center justify-center text-red-500">
                  <User className="w-4 h-4" />
                </div>
                <span className="text-sm font-semibold text-slate-700">CCCD gắn chip / VNeID</span>
              </div>
              <div className="bg-cyan-100 text-cyan-800 text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider">
                Ưu tiên y tế
              </div>
            </button>

            <button className="w-full flex items-center px-4 py-3 border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center">
                <span className="font-bold text-blue-600 text-sm">G</span>
              </div>
              <span className="text-sm font-semibold text-slate-700">Tài khoản Google</span>
            </button>

            <button className="w-full flex items-center justify-between px-4 py-3 border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-500">
                  <MessageSquare className="w-4 h-4" />
                </div>
                <span className="text-sm font-semibold text-slate-700">Mã OTP qua Zalo / SMS</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>

        <div className="mt-8 text-center text-sm">
          <span className="text-slate-500">Chưa có hồ sơ sức khỏe? </span>
          <Link to="/register" className="font-semibold text-sky-600 hover:text-sky-700">
            Đăng ký ngay
          </Link>
        </div>
      </div>

      {/* Footer Security Badge */}
      <div className="mt-6 flex items-center justify-center gap-2 text-xs font-medium text-slate-500">
        <Lock className="w-3.5 h-3.5 text-emerald-600" />
        Mã hóa đầu cuối 256-bit chuẩn bảo mật dữ liệu y tế quốc gia
      </div>
    </div>
  )
}
