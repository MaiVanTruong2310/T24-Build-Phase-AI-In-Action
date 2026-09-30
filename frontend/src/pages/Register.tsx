import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { AppDispatch, RootState } from '../app/store'
import { registerUser, sendOtp, verifyOtp, resetRegisterSuccess } from '../features/auth/authSlice'
import { Eye, EyeOff, User, Lock, ShieldCheck, ArrowRight, Loader2, Phone, Mail, Key } from 'lucide-react'

// TEMPORARY DEMO ONLY: keep this disabled before enabling real OTP delivery.
const TEMPORARY_OTP_BYPASS = true
const TEMPORARY_OTP_CODE = '123456'

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

    /*
     * Original flow kept for restoration:
     * await dispatch(registerUser(payload))
     * The successful registration then displays the manual OTP form below.
     */
    const registrationResult = await dispatch(registerUser(payload))

    // TEMPORARY OTP bypass: ask the mock API for the actual generated code.
    if (TEMPORARY_OTP_BYPASS && registerUser.fulfilled.match(registrationResult)) {
      const otpResult = await dispatch(sendOtp({ phone: formData.phone, purpose: 'register' }))
      if (sendOtp.rejected.match(otpResult)) {
        setValidationError('Không thể lấy OTP tự động. Bạn có thể nhập OTP thủ công.')
        return
      }

      const returnedOtp = otpResult.payload?.otp
      // Keep the fixed mock code only as a fallback for older deployments.
      const generatedOtp = typeof returnedOtp === 'string' && /^\d{6}$/.test(returnedOtp)
        ? returnedOtp
        : TEMPORARY_OTP_CODE
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

  // The original manual OTP screen remains as a fallback if the temporary
  // bypass is disabled or the automatic verification fails.
  if (registerSuccess) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">Xác thực tài khoản</h2>
            <p className="text-sm text-slate-500">
              Vui lòng nhập mã OTP vừa được gửi đến số điện thoại <b>{formData.phone}</b>
            </p>
          </div>

          {(error || validationError) && (
            <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600 flex items-start gap-2">
              <div className="mt-0.5">⚠️</div>
              <p>{validationError || error}</p>
            </div>
          )}

          <form onSubmit={handleVerifyOtp} className="space-y-6">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-900 block">Mã xác thực (OTP)</label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="Nhập 6 chữ số"
                  className="w-full pl-10 pr-4 py-3 text-center tracking-[0.5em] font-bold text-lg rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all bg-white"
                  disabled={loading}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || otpCode.length !== 6}
              className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
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
      <div className="bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-2 bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full text-xs font-semibold mb-4">
            <ShieldCheck className="w-4 h-4" />
            Cổng Đăng Ký Y Tế Số An Toàn
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-3">Tạo tài khoản MediCare AI</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Đăng ký nhanh chóng để quản lý hồ sơ sức khỏe và đặt lịch khám thông minh.
          </p>
        </div>

        <div className="flex gap-4 mb-8">
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200">
            <div className="w-5 h-5 rounded-full bg-red-100 text-red-500 flex items-center justify-center">
              <User className="w-3 h-3" />
            </div>
            <span className="text-sm font-semibold text-slate-700">Đăng ký bằng VNeID</span>
          </button>
          <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200">
            <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center shadow-sm">
              <span className="font-bold text-blue-600 text-xs">G</span>
            </div>
            <span className="text-sm font-semibold text-slate-700">Tài khoản Google</span>
          </button>
        </div>

        <div className="relative flex items-center justify-center mb-8">
          <div className="absolute border-t border-slate-200 w-full"></div>
          <span className="bg-white px-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">
            HOẶC ĐIỀN BIỂU MẪU TRỰC TIẾP
          </span>
        </div>

        {(error || validationError) && (
          <div className="mb-6 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600 flex items-start gap-2">
            <div className="mt-0.5">⚠️</div>
            <p>{validationError || error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 mb-4">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs">1</span>
              Thông tin cá nhân
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Họ và tên <span className="text-red-500">*</span></label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="full_name" value={formData.full_name} onChange={handleChange} placeholder="Nguyễn Văn A" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" disabled={loading} />
                </div>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-900">Email</label>
                  <span className="text-xs text-slate-400 font-medium">Tùy chọn</span>
                </div>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="bacsi@example.com"
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white"
                    disabled={loading}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-900">Số điện thoại <span className="text-red-500">*</span></label>
                  <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                    <Lock className="w-3 h-3" /> Dùng làm tài khoản đăng nhập
                  </span>
                </div>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="phone" value={formData.phone} onChange={handleChange} placeholder="0912 345 678" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" disabled={loading} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-900">Ngày sinh <span className="text-red-500">*</span></label>
                  <input type="date" name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm text-slate-500 bg-white" disabled={loading} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-900">Giới tính <span className="text-red-500">*</span></label>
                  <select name="gender" value={formData.gender} onChange={handleChange} className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm text-slate-500 bg-white" disabled={loading}>
                    <option value="">Chọn giới tính</option>
                    <option value="male">Nam</option>
                    <option value="female">Nữ</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div className="bg-slate-50/50 p-6 rounded-2xl border border-slate-100">
            <div className="flex justify-between items-center mb-4">
              <h3 className="flex items-center gap-2 font-bold text-slate-900">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 text-xs">2</span>
                Định danh y tế
              </h3>
              <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded-md font-medium">Tùy chọn khuyến khích</span>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Số CCCD / Mã định danh cá nhân</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="citizen_id" value={formData.citizen_id} onChange={handleChange} placeholder="12 chữ số" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" disabled={loading} />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-slate-900">Mã số Thẻ Bảo hiểm Y tế (BHYT)</label>
                  <span className="text-xs text-emerald-600 font-medium">Liên thông viện phí</span>
                </div>
                <div className="relative">
                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" name="health_insurance_code" value={formData.health_insurance_code} onChange={handleChange} placeholder="Gồm 15 ký tự - liên thông thanh toán" className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" disabled={loading} />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900 mb-4">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs">3</span>
              Bảo mật tài khoản
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">
                  Mật khẩu <span className="text-xs text-slate-400 font-normal ml-1">(Tùy chọn)</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showPassword ? "text" : "password"} 
                    name="password" value={formData.password} onChange={handleChange}
                    placeholder="Nhập 8 đến 128 ký tự" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" 
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-900">Xác nhận lại mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showConfirmPassword ? "text" : "password"} 
                    name="confirm_password" value={formData.confirm_password} onChange={handleChange}
                    placeholder="Nhập lại mật khẩu vừa tạo" 
                    className="w-full pl-10 pr-10 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all text-sm bg-white" 
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="mt-1 rounded text-sky-600 focus:ring-sky-500/20" />
            <span className="text-sm text-slate-600">
              Tôi đồng ý với <a href="#" className="text-sky-600 font-semibold hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-sky-600 font-semibold hover:underline">Chính sách bảo mật dữ liệu y tế</a> của MediCare AI.
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3.5 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Tạo tài khoản ngay
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-sm">
          <span className="text-slate-500">Đã có tài khoản? </span>
          <Link to="/login" className="font-semibold text-sky-600 hover:text-sky-700">
            Đăng nhập
          </Link>
        </div>
      </div>
    </div>
  )
}
