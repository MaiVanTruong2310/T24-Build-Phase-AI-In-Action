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
      <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8 text-center">
        <div className="w-16 h-16 bg-sky-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Lock className="w-8 h-8 text-sky-600" />
        </div>
        
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Khôi phục mật khẩu</h2>
        {step === 1 ? (
          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            Vui lòng nhập số điện thoại hoặc email đã đăng ký. Chúng tôi sẽ gửi mã xác thực (OTP) để bạn đặt lại mật khẩu mới.
          </p>
        ) : (
          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            Mã OTP đã được gửi đến <strong>{username}</strong>. Vui lòng nhập mã xác thực và mật khẩu mới.
          </p>
        )}

        {(validationError || error) && (
          <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600 flex items-start gap-2">
            <div className="mt-0.5">⚠️</div>
            <p>{validationError || error}</p>
          </div>
        )}

        {step === 1 ? (
          <form onSubmit={handleSubmitStep1} className="space-y-6">
          <div className="space-y-1.5 text-left">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="username">
              Số điện thoại hoặc Email
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nhập thông tin"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm placeholder:text-slate-400 bg-white"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !username}
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
        ) : (
        <form onSubmit={handleSubmitStep2} className="space-y-5">
          <div className="space-y-1.5 text-left">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="otpCode">
              Mã xác thực (OTP)
            </label>
            <input
              id="otpCode"
              type="text"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
              placeholder="Nhập 6 chữ số"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm placeholder:text-slate-400 bg-white text-center tracking-widest font-mono text-lg"
              disabled={loading}
            />
          </div>

          <div className="space-y-1.5 text-left">
            <label className="text-sm font-semibold text-slate-900 block" htmlFor="newPassword">
              Mật khẩu mới
            </label>
            <div className="relative">
              <input
                id="newPassword"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Nhập 8 đến 128 ký tự"
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

          <button
            type="submit"
            disabled={loading || !otpCode || !newPassword}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 mt-4"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              'Đặt lại mật khẩu'
            )}
          </button>
        </form>
        )}

        <div className="mt-8 text-sm">
          <Link to="/login" className="font-semibold text-sky-600 hover:text-sky-700">
            Quay lại đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
