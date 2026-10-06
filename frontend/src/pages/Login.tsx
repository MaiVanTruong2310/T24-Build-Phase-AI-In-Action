import { TypewriterLoader } from '../components/TypewriterLoader';
import { useState, FormEvent, useEffect } from 'react'

import { Link, useNavigate, useLocation } from 'react-router-dom'

import { useDispatch, useSelector } from 'react-redux'

import { AppDispatch, RootState } from '../app/store'

import { loginUser } from '../features/auth/authSlice'

import { Eye, EyeOff, User, ArrowRight, Lock, MessageSquare } from 'lucide-react'



export function Login() {

  const [username, setUsername] = useState('')

  const [password, setPassword] = useState('')

  const [showPassword, setShowPassword] = useState(false)



  const dispatch = useDispatch<AppDispatch>()

  const navigate = useNavigate()

  const location = useLocation()



  const { loading, error, user } = useSelector((state: RootState) => state.auth)



  const [validationError, setValidationError] = useState('')

  const [confirmationNotice, setConfirmationNotice] = useState('')

  useEffect(() => {

    const params = new URLSearchParams(window.location.hash.slice(1))

    if (params.get('type') === 'signup' && params.get('access_token')) {

      setConfirmationNotice('Đã mở liên kết xác nhận email. Vui lòng đăng nhập bằng email và mật khẩu.')

    } else if (params.get('error')) {

      setValidationError('Liên kết xác nhận không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu gửi lại email.')

    }

    if (params.has('access_token') || params.has('error')) window.history.replaceState(null, '', window.location.pathname + window.location.search)

  }, [])



  useEffect(() => {

    if (user) {

      if (user.role === 'staff') {

        navigate('/staff/dieu-phoi')

      } else {

        const returnTo = new URLSearchParams(location.search).get('returnTo');

        navigate(!user.full_name || !user.phone || !user.date_of_birth || !user.gender ? '/patient/profile?complete=1' : returnTo?.startsWith('/') && !returnTo.startsWith('//') && !returnTo.startsWith('/login') ? returnTo : '/patient')

      }

    }

  }, [user, navigate, location.search])



  const handleSubmit = async (e: FormEvent) => {

    e.preventDefault()

    setValidationError('')



    const trimmedUsername = username.trim()

    if (!trimmedUsername) {

      setValidationError('Vui lòng nhập email hoặc tài khoản điều phối.')

      return

    }



    if (trimmedUsername.includes('@') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedUsername)) {

      setValidationError('Vui lòng nhập email hợp lệ.')

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

      <div className="bg-white/95 light:bg-app-surface/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200/90 light:border-app-border/90 dark:border-slate-800/90 shadow-xl dark:shadow-2xl p-6 sm:p-8 text-slate-900 light:text-app-text dark:text-slate-100 transition-colors duration-300">

        {/* Form Header */}

        <div className="flex items-center gap-3.5 mb-3">

          <img

            src="/vcare-logo.png"

            alt="VCare+ Logo"

            className="w-12 h-12 rounded-xl object-contain bg-white light:bg-app-surface dark:bg-slate-900 border border-slate-200 light:border-app-border dark:border-slate-700 shadow-sm shrink-0 p-0.5"

          />

          <div>

            <h2 className="text-xl sm:text-2xl font-bold text-slate-900 light:text-app-text dark:text-slate-100 tracking-tight">

              Đăng Nhập VCare+

            </h2>

            <p className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">Hệ Thống Y Tế Số Đa Tầng</p>

          </div>

        </div>

        <p className="text-xs sm:text-sm text-slate-600 light:text-app-secondary dark:text-slate-400 mb-8 leading-relaxed">

          Chào mừng quay trở lại. Đăng nhập để tiếp tục lộ trình khám bệnh đa tầng và theo dõi bệnh án.

        </p>



        {confirmationNotice && <p role="status" className="mb-4 text-sm text-green-700">{confirmationNotice}</p>}

        {(error || validationError) && (

          <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/40 rounded-xl text-xs sm:text-sm text-red-700 dark:text-red-300 flex items-start gap-2">

            <div className="mt-0.5">⚠️</div>

            <p>{validationError || error}</p>

          </div>

        )}



        <form onSubmit={handleSubmit} className="space-y-5">

          <div className="space-y-1.5">

            <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block" htmlFor="username">

              Email hoặc tài khoản điều phối

            </label>

            <input

              id="username"

              type="text"

              value={username}

              onChange={(e) => setUsername(e.target.value)}

              placeholder="ban@example.com"

              className="w-full px-4 py-3 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60 transition-all"

              disabled={loading}

            />

          </div>



          <div className="space-y-1.5">

            <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block" htmlFor="password">

              Mật khẩu

            </label>

            <div className="relative">

              <input

                id="password"

                type={showPassword ? 'text' : 'password'}

                value={password}

                onChange={(e) => setPassword(e.target.value)}

                placeholder="••••••••••••"

                className="w-full px-4 py-3 rounded-xl border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60 transition-all"

                disabled={loading}

              />

              <button

                type="button"

                onClick={() => setShowPassword(!showPassword)}

                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 light:text-app-secondary hover:text-slate-600 light:hover:text-app-secondary dark:hover:text-slate-200 transition-colors"

                tabIndex={-1}

              >

                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}

              </button>

            </div>

          </div>



          <div className="flex items-center justify-between pt-1">

            <label className="flex items-center gap-2 cursor-pointer">

              <input type="checkbox" className="rounded border-slate-300 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-950 text-blue-600 light:text-app-primary focus:ring-0" />

              <span className="text-xs text-slate-600 light:text-app-secondary dark:text-slate-400">Ghi nhớ đăng nhập</span>

            </label>

            <Link to="/forgot-password" className="text-xs font-medium text-blue-600 light:text-app-primary dark:text-cyan-400 hover:text-blue-700 light:hover:text-app-primary dark:hover:text-cyan-300 transition-colors">

              Quên mật khẩu?

            </Link>

          </div>



          <button

            type="submit"

            disabled={loading || !username || !password}

            className="btn-clinical-primary w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm mt-3"

          >

            {loading ? (

              <>

                <TypewriterLoader />

                <span>Đang xác thực lâm sàng...</span>

              </>

            ) : (

              <>

                <span>Đăng Nhập</span>

                <ArrowRight className="w-4 h-4" />

              </>

            )}

          </button>

        </form>



        <div className="mt-8">

          <div className="relative flex items-center justify-center mb-6">

            <div className="absolute border-t border-slate-200 light:border-app-border dark:border-slate-800 w-full"></div>

            <span className="bg-white light:bg-app-surface dark:bg-slate-900 px-4 text-[10px] font-semibold text-slate-500 light:text-app-secondary dark:text-slate-400 uppercase tracking-wider relative z-10">

              Hoặc đăng nhập bằng

            </span>

          </div>



          <div className="space-y-3">

            <button className="w-full flex items-center justify-between px-4 py-3 border border-slate-200 light:border-app-border dark:border-slate-800 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/50 hover:bg-slate-100 light:hover:bg-app-muted dark:hover:bg-slate-800/60 rounded-xl transition-all">

              <div className="flex items-center gap-3">

                <div className="w-8 h-8 rounded-lg bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/30 flex items-center justify-center text-red-600 dark:text-red-400">

                  <User className="w-4 h-4" />

                </div>

                <span className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-200">CCCD gắn chip / VNeID</span>

              </div>

              <div className="border border-blue-500/20 light:border-app-primary/20 dark:border-cyan-500/30 bg-blue-50 light:bg-app-muted dark:bg-cyan-950/40 text-blue-700 light:text-app-primary dark:text-cyan-300 text-[10px] font-semibold px-2 py-0.5 rounded-md uppercase">

                Ưu tiên y tế

              </div>

            </button>



            <button className="w-full flex items-center px-4 py-3 border border-slate-200 light:border-app-border dark:border-slate-800 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/50 hover:bg-slate-100 light:hover:bg-app-muted dark:hover:bg-slate-800/60 rounded-xl transition-all gap-3">

              <div className="w-8 h-8 rounded-lg bg-slate-100 light:bg-app-muted dark:bg-slate-800 border border-slate-200 light:border-app-border dark:border-slate-700 flex items-center justify-center">

                <span className="font-bold text-blue-600 light:text-app-primary dark:text-blue-400 text-sm">G</span>

              </div>

              <span className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-200">Tài khoản Google</span>

            </button>



            <button className="w-full flex items-center justify-between px-4 py-3 border border-slate-200 light:border-app-border dark:border-slate-800 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/50 hover:bg-slate-100 light:hover:bg-app-muted dark:hover:bg-slate-800/60 rounded-xl transition-all">

              <div className="flex items-center gap-3">

                <div className="w-8 h-8 rounded-lg bg-blue-50 light:bg-app-muted dark:bg-blue-950/60 border border-blue-200 light:border-app-border dark:border-blue-500/30 flex items-center justify-center text-blue-600 light:text-app-primary dark:text-cyan-400">

                  <MessageSquare className="w-4 h-4" />

                </div>

                <span className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-200">Mã OTP qua Zalo / SMS</span>

              </div>

              <ArrowRight className="w-4 h-4 text-slate-400 light:text-app-secondary dark:text-slate-500" />

            </button>

          </div>

        </div>



        <div className="mt-8 text-center text-xs sm:text-sm">

          <span className="text-slate-600 light:text-app-secondary dark:text-slate-400">Chưa có hồ sơ sức khỏe? </span>

          <Link to="/register" className="font-semibold text-blue-600 light:text-app-primary dark:text-cyan-400 hover:text-blue-700 light:hover:text-app-primary dark:hover:text-cyan-300">

            Đăng ký ngay

          </Link>

        </div>

      </div>



      {/* Footer Security Badge */}

      <div className="mt-6 flex items-center justify-center gap-2 text-xs font-normal text-slate-500 light:text-app-secondary dark:text-slate-400">

        <Lock className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />

        <span>Mã hóa đầu cuối 256-bit chuẩn bảo mật y tế HIPAA & Bộ Y Tế</span>

      </div>

    </div>

  )

}



