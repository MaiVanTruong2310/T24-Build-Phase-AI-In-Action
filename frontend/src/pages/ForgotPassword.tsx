import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { Lock, ArrowRight, Loader2, Eye, EyeOff } from 'lucide-react'
import { AppDispatch, RootState } from '../app/store'
import { requestPasswordReset, resetPassword } from '../features/auth/authSlice'

export function ForgotPassword() {
  const [step, setStep] = useState<1 | 2>(1)
  const [username, setUsername] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [validationError, setValidationError] = useState('')

  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { loading, error } = useSelector((state: RootState) => state.auth)

  const handleSubmitStep1 = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')

    if (username.length < 7) {
      setValidationError('Tên đăng nhập (Email/SĐT) quá ngắn.')
      return
    }

    const res = await dispatch(requestPasswordReset(username))
    if (requestPasswordReset.fulfilled.match(res)) {
      // Temporary mock OTP support: the API returns the generated code while
      // MockOtpProvider is active, so fill it into the existing OTP field.
      const returnedOtp = (res.payload as { otp?: unknown } | undefined)?.otp
      if (typeof returnedOtp === 'string' && /^\d{6}$/.test(returnedOtp)) {
        setOtpCode(returnedOtp)
      }
      setStep(2)
    }
  }

  const handleSubmitStep2 = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')

    if (!otpCode || otpCode.length !== 6) {
      setValidationError('Vui lòng nhập mã OTP 6 chữ số.')
      return
    }

    if (newPassword.length < 8 || newPassword.length > 128) {
      setValidationError('Mật khẩu mới phải từ 8 đến 128 ký tự.')
      return
    }

    const res = await dispatch(resetPassword({ username, code: otpCode, new_password: newPassword }))
    if (resetPassword.fulfilled.match(res)) {
      alert('Đổi mật khẩu thành công! Vui lòng đăng nhập lại.')
      navigate('/login')
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="bg-white/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200/90 dark:border-slate-800/90 shadow-xl dark:shadow-2xl p-6 sm:p-8 text-center text-slate-900 dark:text-slate-100 transition-colors duration-300">
        <div className="w-16 h-16 bg-blue-50 dark:bg-blue-950/60 border border-blue-100 dark:border-blue-900/40 rounded-full flex items-center justify-center mx-auto mb-6">
          <Lock className="w-8 h-8 text-blue-600 dark:text-blue-400" />
        </div>
        
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">Khôi phục mật khẩu</h2>
        {step === 1 ? (
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mb-8 leading-relaxed">
            Vui lòng nhập số điện thoại hoặc email đã đăng ký. Chúng tôi sẽ gửi mã xác thực (OTP) để bạn đặt lại mật khẩu mới.
          </p>
        ) : (
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mb-8 leading-relaxed">
            Mã OTP đã được gửi đến <strong>{username}</strong>. Vui lòng nhập mã xác thực và mật khẩu mới.
          </p>
        )}

        {(validationError || error) && (
          <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/40 rounded-xl text-xs sm:text-sm text-red-700 dark:text-red-300 flex items-start gap-2 text-left">
            <div className="mt-0.5">⚠️</div>
            <p>{validationError || error}</p>
          </div>
        )}

        {step === 1 ? (
          <form onSubmit={handleSubmitStep1} className="space-y-6">
          <div className="space-y-1.5 text-left">
            <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block" htmlFor="username">
              Số điện thoại hoặc Email
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nhập thông tin"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !username}
            className="btn-clinical-primary w-full py-3.5 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <span>Gửi mã xác thực</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
        ) : (
        <form onSubmit={handleSubmitStep2} className="space-y-5">
          <div className="space-y-1.5 text-left">
            <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block" htmlFor="otpCode">
              Mã xác thực (OTP)
            </label>
            <input
              id="otpCode"
              type="text"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
              placeholder="Nhập 6 chữ số"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all text-center tracking-[0.5em] font-mono font-bold text-lg"
              disabled={loading}
            />
          </div>

          <div className="space-y-1.5 text-left">
            <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block" htmlFor="newPassword">
              Mật khẩu mới
            </label>
            <div className="relative">
              <input
                id="newPassword"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Nhập 8 đến 128 ký tự"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !otpCode || !newPassword}
            className="btn-clinical-primary w-full py-3.5 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm mt-4"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              'Đặt lại mật khẩu'
            )}
          </button>
        </form>
        )}

        <div className="mt-8 text-xs sm:text-sm">
          <Link to="/login" className="font-semibold text-blue-600 dark:text-cyan-400 hover:text-blue-700 dark:hover:text-cyan-300">
            Quay lại đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
