import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { AppDispatch, RootState } from '../app/store'
import { registerUser, sendOtp, resetRegisterSuccess } from '../features/auth/authSlice'
import { Eye, EyeOff, User, Lock, ShieldCheck, ArrowRight, Loader2, Phone, Mail, AlertCircle } from 'lucide-react'


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
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [validationError, setValidationError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [agreeTerms, setAgreeTerms] = useState(false)

  const dispatch = useDispatch<AppDispatch>()
  
  const { loading, error, registerSuccess } = useSelector((state: RootState) => state.auth)

  const validateForm = () => {
    const errors: Record<string, string> = {}
    if (!formData.email.trim()) errors.email = 'Vui lòng nhập email để xác thực tài khoản.'
    if (!formData.password) errors.password = 'Vui lòng tạo mật khẩu để đăng nhập.'

    // 1. Họ và tên
    const trimmedName = formData.full_name.trim()
    if (!trimmedName) {
      errors.full_name = 'Vui lòng nhập họ và tên.'
    } else if (trimmedName.length < 2 || trimmedName.length > 200) {
      errors.full_name = 'Họ và tên phải có độ dài từ 2 đến 200 ký tự.'
    }

    // 2. Số điện thoại (10 chữ số chuẩn VN, đầu 03, 05, 07, 08, 09 hoặc +84)
    const phoneClean = formData.phone.trim().replace(/[\s.-]/g, '')
    const phoneRegex = /^(0|\+84)(3|5|7|8|9)[0-9]{8}$/
    if (!phoneClean) {
      errors.phone = 'Vui lòng nhập số điện thoại.'
    } else if (!phoneRegex.test(phoneClean)) {
      errors.phone = 'Số điện thoại không hợp lệ (10 số, đầu số 03, 05, 07, 08, 09).'
    }

    // 3. Email (Tùy chọn, nhưng nếu nhập phải đúng chuẩn)
    const emailTrimmed = formData.email.trim()
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    if (emailTrimmed && !emailRegex.test(emailTrimmed)) {
      errors.email = 'Email không đúng định dạng (VD: benhnhan@example.com).'
    }

    // 4. Ngày sinh (Bắt buộc, không được vượt quá hiện tại)
    if (!formData.date_of_birth) {
      errors.date_of_birth = 'Vui lòng chọn ngày sinh.'
    } else {
      const dob = new Date(formData.date_of_birth)
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      if (isNaN(dob.getTime())) {
        errors.date_of_birth = 'Ngày sinh không hợp lệ.'
      } else if (dob >= today) {
        errors.date_of_birth = 'Ngày sinh phải trong quá khứ (không được vượt quá hôm nay).'
      } else if (dob.getFullYear() < 1900) {
        errors.date_of_birth = 'Năm sinh không hợp lệ (từ 1900 trở lại đây).'
      }
    }

    // 5. Giới tính
    if (!formData.gender) {
      errors.gender = 'Vui lòng chọn giới tính.'
    }

    // 6. Số CCCD (Tùy chọn, nhưng nếu nhập thì đúng chính xác 12 chữ số)
    const citizenIdTrimmed = formData.citizen_id.trim()
    const cccdRegex = /^\d{12}$/
    if (citizenIdTrimmed && !cccdRegex.test(citizenIdTrimmed)) {
      errors.citizen_id = 'Số CCCD phải gồm chính xác 12 chữ số.'
    }

    // 7. Mã BHYT (Tùy chọn, 10-15 ký tự chữ/số)
    const bhiTrimmed = formData.health_insurance_code.trim()
    const bhiRegex = /^[a-zA-Z0-9]{10,15}$/
    if (bhiTrimmed && !bhiRegex.test(bhiTrimmed)) {
      errors.health_insurance_code = 'Mã số BHYT phải gồm từ 10 đến 15 ký tự chữ và số.'
    }

    // 8. Mật khẩu & Xác nhận mật khẩu (Tùy chọn, nhưng nếu nhập phải từ 8-128 ký tự và khớp)
    if (formData.password) {
      if (formData.password.length < 8 || formData.password.length > 128) {
        errors.password = 'Mật khẩu phải có độ dài từ 8 đến 128 ký tự.'
      }
      if (formData.password !== formData.confirm_password) {
        errors.confirm_password = 'Mật khẩu xác nhận không khớp.'
      }
    } else if (formData.confirm_password) {
      errors.password = 'Vui lòng nhập mật khẩu.'
    }

    // 9. Bắt buộc đồng ý điều khoản dịch vụ
    if (!agreeTerms) {
      errors.agreeTerms = 'Bạn cần đồng ý với Điều khoản dịch vụ và Chính sách bảo mật.'
    }

    return errors
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }))
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setValidationError('')

    const errors = validateForm()
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setValidationError('Vui lòng kiểm tra và hoàn thiện các mục còn thiếu hoặc chưa đúng bên dưới.')
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

    await dispatch(registerUser(payload))
  }

  if (registerSuccess) {
    return (
      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
        <Mail className="mb-4 h-10 w-10 text-blue-600" />
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Xác nhận email của bạn</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">Vui lòng kiểm tra hộp thư <strong>{formData.email}</strong> và mở liên kết xác nhận. Bạn cần xác nhận email trước khi đăng nhập.</p>
        <p className="mt-2 text-xs text-slate-500">Nếu chưa thấy thư, hãy kiểm tra mục Spam. Số điện thoại được giữ làm thông tin liên hệ.</p>
        {(error || validationError) && <p role="alert" className="mt-3 text-sm text-red-600">{validationError || error}</p>}
        <button type="button" disabled={loading} onClick={async () => { const result = await dispatch(sendOtp({ email: formData.email, purpose: 'register' })); if (sendOtp.fulfilled.match(result)) setValidationError('Đã yêu cầu gửi lại email xác nhận.'); }} className="mt-5 w-full rounded-xl border border-blue-200 px-4 py-3 text-sm font-semibold text-blue-600 disabled:opacity-50">{loading ? 'Đang gửi…' : 'Gửi lại email xác nhận'}</button>
        <Link to="/login" onClick={() => dispatch(resetRegisterSuccess())} className="mt-3 block rounded-xl bg-blue-600 px-4 py-3 text-center text-sm font-semibold text-white">Đến trang đăng nhập</Link>
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
                  <input
                    type="text"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                    placeholder="Nguyễn Văn A"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.full_name
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                </div>
                {fieldErrors.full_name && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.full_name}</span>
                  </p>
                )}
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Email *</label>
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Dùng để xác thực</span>
                </div>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="benhnhan@example.com"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.email
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                </div>
                {fieldErrors.email && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.email}</span>
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Số điện thoại <span className="text-red-500">*</span></label>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                    <Lock className="w-3 h-3" /> Thông tin liên hệ
                  </span>
                </div>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    name="phone"
                    maxLength={12}
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="0912 345 678"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.phone
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                </div>
                {fieldErrors.phone && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.phone}</span>
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Ngày sinh <span className="text-red-500">*</span></label>
                  <input
                    type="date"
                    name="date_of_birth"
                    max={new Date().toISOString().split('T')[0]}
                    value={formData.date_of_birth}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.date_of_birth
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                  {fieldErrors.date_of_birth && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{fieldErrors.date_of_birth}</span>
                    </p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Giới tính <span className="text-red-500">*</span></label>
                  <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.gender
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  >
                    <option value="" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Chọn giới tính</option>
                    <option value="male" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Nam</option>
                    <option value="female" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">Nữ</option>
                  </select>
                  {fieldErrors.gender && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{fieldErrors.gender}</span>
                    </p>
                  )}
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
                  <input
                    type="text"
                    name="citizen_id"
                    maxLength={12}
                    value={formData.citizen_id}
                    onChange={handleChange}
                    placeholder="12 chữ số (VD: 001201012345)"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.citizen_id
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                </div>
                {fieldErrors.citizen_id && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.citizen_id}</span>
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Mã số Thẻ Bảo hiểm Y tế (BHYT)</label>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Liên thông viện phí</span>
                </div>
                <div className="relative">
                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    name="health_insurance_code"
                    maxLength={15}
                    value={formData.health_insurance_code}
                    onChange={handleChange}
                    placeholder="Gồm 10 đến 15 ký tự chữ và số"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.health_insurance_code
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                </div>
                {fieldErrors.health_insurance_code && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.health_insurance_code}</span>
                  </p>
                )}
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
                  Mật khẩu * <span className="text-xs text-slate-500 dark:text-slate-400 font-normal ml-1">(Bắt buộc)</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showPassword ? "text" : "password"} 
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Nhập 8 đến 128 ký tự" 
                    className={`w-full pl-10 pr-10 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.password
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.password}</span>
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 block">Xác nhận lại mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input 
                    type={showConfirmPassword ? "text" : "password"} 
                    name="confirm_password"
                    value={formData.confirm_password}
                    onChange={handleChange}
                    placeholder="Nhập lại mật khẩu vừa tạo" 
                    className={`w-full pl-10 pr-10 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.confirm_password
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 dark:border-slate-700/80 bg-slate-50/80 dark:bg-slate-950/60 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-cyan-500/60'
                    }`}
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {fieldErrors.confirm_password && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{fieldErrors.confirm_password}</span>
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={agreeTerms}
                onChange={(e) => {
                  setAgreeTerms(e.target.checked)
                  if (fieldErrors.agreeTerms) {
                    setFieldErrors((prev) => ({ ...prev, agreeTerms: '' }))
                  }
                }}
                className={`mt-1 rounded bg-white dark:bg-slate-950 text-blue-600 focus:ring-blue-500/20 cursor-pointer ${
                  fieldErrors.agreeTerms ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 dark:border-slate-700'
                }`}
              />
              <span className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
                Tôi đồng ý với <a href="#" className="text-blue-600 dark:text-cyan-400 font-semibold hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-blue-600 dark:text-cyan-400 font-semibold hover:underline">Chính sách bảo mật dữ liệu y tế</a> của VCare+.
              </span>
            </label>
            {fieldErrors.agreeTerms && (
              <p className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1 font-medium">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{fieldErrors.agreeTerms}</span>
              </p>
            )}
          </div>

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
