import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { AppDispatch, RootState } from '../app/store'
import { registerUser, sendOtp, verifyOtp, resetRegisterSuccess } from '../features/auth/authSlice'
import { Eye, EyeOff, User, Lock, ShieldCheck, ArrowRight, Loader2, Phone, Mail, Key } from 'lucide-react'

const AUTO_VERIFY_MOCK_OTP = true
const DEFAULT_MOCK_OTP = '123456'

export function Register() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    gender: '',
    citizen_id: '',
    health_insurance_code: '',
    password: '',
    confirm_password: ''
  })
  const [otpCode, setOtpCode] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [validationError, setValidationError] = useState('')

  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  
  const { loading, error, registerSuccess } = useSelector((state: RootState) => state.auth)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')

    if (formData.password) {
      if (formData.password.length < 8 || formData.password.length > 128) {
        setValidationError('Mật khẩu phải có độ dài từ 8 đến 128 ký tự.')
        return
      }
      if (formData.password !== formData.confirm_password) {
        setValidationError('Mật khẩu xác nhận không khớp.')
        return
      }
    }

    if (!formData.full_name || !formData.phone || !formData.date_of_birth || !formData.gender) {
      setValidationError('Vui lòng điền đầy đủ các trường bắt buộc (*).')
      return
    }

    const payload = {
      full_name: formData.full_name,
      ...(formData.email.trim() && { email: formData.email.trim() }),
      phone: formData.phone,
      date_of_birth: formData.date_of_birth,
      gender: formData.gender,
      ...(formData.password && { password: formData.password }),
      ...(formData.citizen_id && { citizen_id: formData.citizen_id }),
      ...(formData.health_insurance_code && { health_insurance_code: formData.health_insurance_code }),
    }

    const registrationResult = await dispatch(registerUser(payload))

    if (AUTO_VERIFY_MOCK_OTP && registerUser.fulfilled.match(registrationResult)) {
      const otpResult = await dispatch(sendOtp({ phone: formData.phone, purpose: 'register' }))
      if (sendOtp.rejected.match(otpResult)) {
        setValidationError('Không thể lấy OTP tự động. Bạn có thể nhập OTP thủ công.')
        return
      }

      const returnedOtp = otpResult.payload?.otp
      const generatedOtp = typeof returnedOtp === 'string' && /^\d{6}$/.test(returnedOtp)
        ? returnedOtp
        : DEFAULT_MOCK_OTP
      setOtpCode(generatedOtp)
      const verificationResult = await dispatch(verifyOtp({ phone: formData.phone, code: generatedOtp }))

      if (verifyOtp.fulfilled.match(verificationResult)) {
        alert('Đăng ký thành công! Vui lòng đăng nhập.')
        dispatch(resetRegisterSuccess())
        navigate('/login')
      }
    }
  }

  const handleVerifyOtp = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')
    if (!otpCode || otpCode.length !== 6) {
      setValidationError('Vui lòng nhập mã OTP 6 chữ số.')
      return
    }

    const res = await dispatch(verifyOtp({ phone: formData.phone, code: otpCode }))
    if (verifyOtp.fulfilled.match(res)) {
      alert('Xác thực thành công! Vui lòng đăng nhập.')
      dispatch(resetRegisterSuccess())
      navigate('/login')
    }
  }

  if (registerSuccess) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200/90 dark:border-slate-800/90 shadow-xl dark:shadow-2xl p-6 sm:p-8 text-slate-900 dark:text-slate-100 transition-colors duration-300">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-3">Xác thực tài khoản</h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Vui lòng nhập mã OTP vừa được gửi đến số điện thoại <b>{formData.phone}</b>
            </p>
          </div>

          {(error || validationError) && (
            <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/40 rounded-xl text-xs sm:text-sm text-red-700 dark:text-red-300 flex items-start gap-2">
              <div className="mt-0.5">⚠️</div>
              <p>{validationError || error}</p>
            </div>
          )}

          <form onSubmit={handleVerifyOtp} className="space-y-6">
            <div className="space-y-1.5">
              <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Mã xác thực (OTP)</label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="Nhập 6 chữ số"
                  className="w-full pl-10 pr-4 py-3 text-center tracking-[0.5em] font-bold text-lg rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all"
                  disabled={loading}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || otpCode.length !== 6}
              className="btn-clinical-primary w-full py-3.5 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Xác nhận OTP'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-white/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200/90 dark:border-slate-800/90 shadow-xl dark:shadow-2xl p-6 sm:p-8 text-slate-900 dark:text-slate-100 transition-colors duration-300">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-4">
            <img
              src="/vcare-logo.png"
              alt="VCare+ Logo"
              className="w-14 h-14 rounded-2xl object-contain bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm p-1"
            />
          </div>
          <div className="flex items-center justify-center">
            <div className="inline-flex items-center justify-center gap-2 border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 px-3 py-1.5 rounded-full text-xs font-semibold mb-3">
              <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              Cổng Đăng Ký Y Tế Số An Toàn
            </div>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2 tracking-tight">Tạo tài khoản VCare+</h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
            Đăng ký nhanh chóng để quản lý hồ sơ sức khỏe và đặt lịch khám thông minh.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50/80 dark:bg-slate-950/50 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-xl transition-all border border-slate-200 dark:border-slate-800">
            <div className="w-5 h-5 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 flex items-center justify-center">
              <User className="w-3 h-3" />
            </div>
            <span className="text-xs sm:text-sm font-semibold text-slate-700 dark:text-slate-200">Đăng ký bằng VNeID</span>
          </button>
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50/80 dark:bg-slate-950/50 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-xl transition-all border border-slate-200 dark:border-slate-800">
            <div className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center shadow-sm">
              <span className="font-bold text-blue-600 dark:text-blue-400 text-xs">G</span>
            </div>
            <span className="text-xs sm:text-sm font-semibold text-slate-700 dark:text-slate-200">Tài khoản Google</span>
          </button>
        </div>

        <div className="relative flex items-center justify-center mb-8">
          <div className="absolute border-t border-slate-200 dark:border-slate-800 w-full"></div>
          <span className="bg-white dark:bg-slate-900 px-4 text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider relative z-10">
            HOẶC ĐIỀN BIỂU MẪU TRỰC TIẾP
          </span>
        </div>

        {(error || validationError) && (
          <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-500/40 rounded-xl text-xs sm:text-sm text-red-700 dark:text-red-300 flex items-start gap-2">
            <div className="mt-0.5">⚠️</div>
            <p>{validationError || error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100 mb-4 text-sm sm:text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 text-xs font-bold">1</span>
              Thông tin cá nhân
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Họ và tên <span className="text-red-500">*</span></label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="full_name" value={formData.full_name} onChange={handleChange} placeholder="Nguyễn Văn A" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" disabled={loading} />
                </div>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Email</label>
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Tùy chọn</span>
                </div>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="benhnhan@example.com"
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all"
                    disabled={loading}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Số điện thoại <span className="text-red-500">*</span></label>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                    <Lock className="w-3 h-3" /> Dùng làm tài khoản đăng nhập
                  </span>
                </div>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="phone" value={formData.phone} onChange={handleChange} placeholder="0912 345 678" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" disabled={loading} />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Ngày sinh <span className="text-red-500">*</span></label>
                  <input type="date" name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all text-sm" disabled={loading} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Giới tính <span className="text-red-500">*</span></label>
                  <select name="gender" value={formData.gender} onChange={handleChange} className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all text-sm" disabled={loading}>
                    <option value="" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Chọn giới tính</option>
                    <option value="male" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Nam</option>
                    <option value="female" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Nữ</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div className="bg-slate-50/70 dark:bg-slate-950/50 p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800/80">
            <div className="flex justify-between items-center mb-4">
              <h3 className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100 text-sm sm:text-base">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 text-xs font-bold">2</span>
                Định danh y tế
              </h3>
              <span className="text-xs bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 rounded-md font-medium">Tùy chọn khuyến khích</span>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Số CCCD / Mã định danh cá nhân</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="citizen_id" value={formData.citizen_id} onChange={handleChange} placeholder="12 chữ số" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" disabled={loading} />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Mã số Thẻ Bảo hiểm Y tế (BHYT)</label>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Liên thông viện phí</span>
                </div>
                <div className="relative">
                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="health_insurance_code" value={formData.health_insurance_code} onChange={handleChange} placeholder="Gồm 15 ký tự - liên thông thanh toán" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" disabled={loading} />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100 mb-4 text-sm sm:text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 text-xs font-bold">3</span>
              Bảo mật tài khoản
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">
                  Mật khẩu <span className="text-xs text-slate-500 dark:text-slate-400 font-normal ml-1">(Tùy chọn)</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showPassword ? "text" : "password"} 
                    name="password" value={formData.password} onChange={handleChange}
                    placeholder="Nhập 8 đến 128 ký tự" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" 
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Xác nhận lại mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showConfirmPassword ? "text" : "password"} 
                    name="confirm_password" value={formData.confirm_password} onChange={handleChange}
                    placeholder="Nhập lại mật khẩu vừa tạo" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60 transition-all" 
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="mt-1 rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-blue-600 focus:ring-blue-500/20" />
            <span className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              Tôi đồng ý với <a href="#" className="text-blue-600 dark:text-cyan-400 font-semibold hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-blue-600 dark:text-cyan-400 font-semibold hover:underline">Chính sách bảo mật dữ liệu y tế</a> của VCare+.
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="btn-clinical-primary w-full py-3.5 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <span>Tạo tài khoản ngay</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-xs sm:text-sm">
          <span className="text-slate-600 dark:text-slate-400">Đã có tài khoản? </span>
          <Link to="/login" className="font-semibold text-blue-600 dark:text-cyan-400 hover:text-blue-700 dark:hover:text-cyan-300">
            Đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
