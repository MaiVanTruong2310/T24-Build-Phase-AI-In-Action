import { TypewriterLoader } from '../components/TypewriterLoader';
import { useState, FormEvent } from 'react'

import { Link } from 'react-router-dom'

import { useDispatch, useSelector } from 'react-redux'

import { AppDispatch, RootState } from '../app/store'

import { registerUser, sendOtp, verifyOtp, resetRegisterSuccess } from '../features/auth/authSlice'

import { Eye, EyeOff, User, Lock, ShieldCheck, ArrowRight, Phone, Mail, AlertCircle } from 'lucide-react'
import {
  birthDateError,
  citizenIdError,
  emailError,
  formatDateVN,
  healthInsuranceCodeError,
} from '../features/appointment-booking/dateValidation'
import { DateInputVN } from '../components/DateInputVN'





export function Register() {

  const [formData, setFormData] = useState({

    full_name: '',
    address: '',

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

  const [emailVerified, setEmailVerified] = useState(false)

  const [confirmationNotice, setConfirmationNotice] = useState('')

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



    // 3. Email / Gmail (Bắt buộc, chuẩn định dạng)
    const errMail = emailError(formData.email)
    if (errMail) {
      errors.email = errMail
    }

    // 4. Ngày sinh (Bắt buộc, chuẩn dd/mm/yyyy, không ở tương lai, không quá 150 tuổi)
    const dobError = birthDateError(formData.date_of_birth)
    if (dobError) {
      errors.date_of_birth = dobError
    }

    // 5. Giới tính
    if (!formData.gender) {
      errors.gender = 'Vui lòng chọn giới tính.'
    }

    // 6. Số CCCD (Tùy chọn, nếu nhập phải đúng 12 chữ số)
    if (formData.citizen_id.trim()) {
      const cccdErr = citizenIdError(formData.citizen_id)
      if (cccdErr) errors.citizen_id = cccdErr
    }

    // 7. Mã BHYT (Tùy chọn, 10-15 ký tự chữ/số)
    if (formData.health_insurance_code.trim()) {
      const bhytErr = healthInsuranceCodeError(formData.health_insurance_code)
      if (bhytErr) errors.health_insurance_code = bhytErr
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



  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement> | { target: { name: string; value: string } }
  ) => {

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
      address: formData.address.trim() || undefined,

      ...(formData.email.trim() && { email: formData.email.trim() }),

      phone: formData.phone,

      date_of_birth: formData.date_of_birth,

      gender: formData.gender,

      ...(formData.password && { password: formData.password }),

      ...(formData.citizen_id && { citizen_id: formData.citizen_id }),

      ...(formData.health_insurance_code && { health_insurance_code: formData.health_insurance_code }),

    }



    const resultAction = await dispatch(registerUser(payload))
    if (registerUser.rejected.match(resultAction)) {
      const errMsg = String(resultAction.payload || resultAction.error?.message || '')
      const lower = errMsg.toLowerCase()
      if (lower.includes('cccd') || lower.includes('citizen_id')) {
        setFieldErrors(prev => ({ ...prev, citizen_id: errMsg }))
      } else if (lower.includes('bảo hiểm') || lower.includes('health_insurance')) {
        setFieldErrors(prev => ({ ...prev, health_insurance_code: errMsg }))
      } else if (lower.includes('phone') || lower.includes('số điện thoại')) {
        setFieldErrors(prev => ({ ...prev, phone: errMsg }))
      } else if (lower.includes('email') || lower.includes('tài khoản đã tồn tại')) {
        setFieldErrors(prev => ({ ...prev, email: errMsg }))
      }
    }
  }



  if (registerSuccess) {

    return (

      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">

        <Mail className="mb-4 h-10 w-10 text-blue-600 light:text-app-primary" />

        <h2 className="text-xl font-bold text-slate-900 light:text-app-text dark:text-white">Xác nhận email của bạn</h2>

        <p className="mt-3 text-sm leading-relaxed text-slate-600 light:text-app-secondary dark:text-slate-300">{emailVerified ? 'Email đã được xác nhận. Bạn có thể đăng nhập bằng email và mật khẩu.' : <>Vui lòng nhập mã OTP 6 chữ số gửi đến <strong>{formData.email}</strong>, hoặc mở liên kết xác nhận trong email.</>}</p>

        {!emailVerified && <form className="mt-5 space-y-3" onSubmit={async (event) => {

          event.preventDefault(); setValidationError(''); setConfirmationNotice('')

          if (!/^\d{6}$/.test(otpCode)) { setValidationError('Vui lòng nhập đủ 6 chữ số OTP.'); return }

          const result = await dispatch(verifyOtp({ email: formData.email.trim().toLowerCase(), code: otpCode }))

          if (verifyOtp.fulfilled.match(result)) { setEmailVerified(true); setOtpCode('') }

        }}>

          <label htmlFor="email-otp" className="block text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-200">Mã OTP email</label>

          <input id="email-otp" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={otpCode} onChange={event => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="Nhập 6 chữ số" disabled={loading} className="w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface px-4 py-3 text-center text-xl tracking-[0.3em] dark:border-slate-600 dark:bg-slate-950" />

          <button type="submit" disabled={loading || otpCode.length !== 6} className="w-full rounded-xl bg-blue-600 light:bg-app-primary px-4 py-3 font-semibold text-white disabled:opacity-50">{loading ? 'Đang xác nhận…' : 'Xác nhận OTP'}</button>

        </form>}

        {confirmationNotice && <p role="status" className="mt-3 text-sm text-green-700">{confirmationNotice}</p>}

        <p className="mt-2 text-xs text-slate-500 light:text-app-secondary">Nếu chưa thấy thư, hãy kiểm tra mục Spam. Số điện thoại được giữ làm thông tin liên hệ.</p>

        {(error || validationError) && <p role="alert" className="mt-3 text-sm text-red-600">{validationError || error}</p>}

        <button type="button" disabled={loading || emailVerified} onClick={async () => { setValidationError(''); setConfirmationNotice(''); const result = await dispatch(sendOtp({ email: formData.email.trim().toLowerCase(), purpose: 'register' })); if (sendOtp.fulfilled.match(result)) setConfirmationNotice('Đã yêu cầu gửi lại email chứa mã OTP.'); }} className="mt-5 w-full rounded-xl border border-blue-200 light:border-app-border px-4 py-3 text-sm font-semibold text-blue-600 light:text-app-primary disabled:opacity-50">{loading ? 'Đang gửi…' : 'Gửi lại email xác nhận'}</button>

        <Link to="/login" onClick={() => dispatch(resetRegisterSuccess())} className="mt-3 block rounded-xl bg-blue-600 light:bg-app-primary px-4 py-3 text-center text-sm font-semibold text-white">Đến trang đăng nhập</Link>

      </div>

    )

  }



  return (

    <div className="w-full max-w-2xl mx-auto">

      <div className="bg-white/95 light:bg-app-surface/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200/90 light:border-app-border/90 dark:border-slate-800/90 shadow-xl dark:shadow-2xl p-6 sm:p-8 text-slate-900 light:text-app-text dark:text-slate-100 transition-colors duration-300">

        <div className="text-center mb-8">

          <div className="inline-flex items-center justify-center mb-4">

            <img

              src="/vcare-logo.png"

              alt="VCare+ Logo"

              className="w-14 h-14 rounded-2xl object-contain bg-white light:bg-app-surface dark:bg-slate-900 border border-slate-200 light:border-app-border dark:border-slate-700 shadow-sm p-1"

            />

          </div>

          <div className="flex items-center justify-center">

            <div className="inline-flex items-center justify-center gap-2 border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 px-3 py-1.5 rounded-full text-xs font-semibold mb-3">

              <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />

              Cổng Đăng Ký Y Tế Số An Toàn

            </div>

          </div>

          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-2 tracking-tight">Tạo tài khoản VCare+</h2>

          <p className="text-xs sm:text-sm text-slate-600 light:text-app-secondary dark:text-slate-400 max-w-md mx-auto leading-relaxed">

            Đăng ký nhanh chóng để quản lý hồ sơ sức khỏe và đặt lịch khám thông minh.

          </p>

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

            <h3 className="flex items-center gap-2 font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 text-sm sm:text-base">

              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 light:bg-app-tint dark:bg-blue-950/60 text-blue-600 light:text-app-primary dark:text-blue-400 text-xs font-bold">1</span>

              Thông tin cá nhân

            </h3>

            

            <div className="space-y-4">

              <div className="space-y-1.5">

                <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Họ và tên <span className="text-red-500">*</span></label>

                <div className="relative">

                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

                  <input

                    type="text"

                    name="full_name"

                    value={formData.full_name}

                    onChange={handleChange}

                    placeholder="Nguyễn Văn A"

                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${

                      fieldErrors.full_name

                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

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

                  <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Email *</label>

                  <span className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 font-medium">Dùng để xác thực</span>

                </div>

                <div className="relative">

                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

                  <input

                    type="email"

                    name="email"

                    value={formData.email}

                    onChange={handleChange}

                    placeholder="benhnhan@example.com"

                    className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${

                      fieldErrors.email

                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

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

                  <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Số điện thoại <span className="text-red-500">*</span></label>

                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">

                    <Lock className="w-3 h-3" /> Thông tin liên hệ

                  </span>

                </div>

                <div className="relative">

                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

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

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

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

                  <div className="flex items-center justify-between">
                    <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">
                      Ngày sinh <span className="text-red-500">*</span> <span className="text-xs font-normal text-slate-500 light:text-app-secondary dark:text-slate-400">(dd/mm/yyyy)</span>
                    </label>
                  </div>

                  <DateInputVN
                    id="date_of_birth"
                    name="date_of_birth"
                    max={new Date().toISOString().split('T')[0]}
                    value={formData.date_of_birth}
                    onChange={handleChange}
                    disabled={loading}
                    hasError={Boolean(fieldErrors.date_of_birth)}
                    placeholder="dd/mm/yyyy"
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${
                      fieldErrors.date_of_birth
                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'
                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'
                    }`}
                  />

                  {fieldErrors.date_of_birth && (

                    <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1 font-medium">

                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />

                      <span>{fieldErrors.date_of_birth}</span>

                    </p>

                  )}

                </div>

                <div className="space-y-1.5">

                  <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Giới tính <span className="text-red-500">*</span></label>

                  <select

                    name="gender"

                    value={formData.gender}

                    onChange={handleChange}

                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${

                      fieldErrors.gender

                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

                    }`}

                    disabled={loading}

                  >

                    <option value="" className="bg-white light:bg-app-surface dark:bg-slate-900 text-slate-900 light:text-app-text dark:text-slate-100">Chọn giới tính</option>

                    <option value="male" className="bg-white light:bg-app-surface dark:bg-slate-900 text-slate-900 light:text-app-text dark:text-slate-100">Nam</option>

                    <option value="female" className="bg-white light:bg-app-surface dark:bg-slate-900 text-slate-900 light:text-app-text dark:text-slate-100">Nữ</option>

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

          <div className="bg-slate-50/70 light:bg-app-page/70 dark:bg-slate-950/50 p-6 rounded-2xl border border-slate-200/80 light:border-app-border/80 dark:border-slate-800/80">

            <div className="flex justify-between items-center mb-4">

              <h3 className="flex items-center gap-2 font-bold text-slate-900 light:text-app-text dark:text-slate-100 text-sm sm:text-base">

                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 text-xs font-bold">2</span>

                Định danh y tế

              </h3>

              <span className="text-xs bg-slate-200 light:bg-app-tint dark:bg-slate-800 text-slate-700 light:text-app-text dark:text-slate-300 px-2 py-1 rounded-md font-medium">Tùy chọn khuyến khích</span>

            </div>

            

            <div className="space-y-4">

              <div className="space-y-1.5">

                <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Số CCCD / Mã định danh cá nhân</label>

                <div className="relative">

                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

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

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

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

                  <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Mã số Thẻ Bảo hiểm Y tế (BHYT)</label>

                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Liên thông viện phí</span>

                </div>

                <div className="relative">

                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

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

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

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

            <h3 className="flex items-center gap-2 font-bold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 text-sm sm:text-base">

              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 light:bg-app-tint dark:bg-blue-950/60 text-blue-600 light:text-app-primary dark:text-blue-400 text-xs font-bold">3</span>

              Bảo mật tài khoản

            </h3>

            

            <div className="space-y-4">

              <div className="space-y-1.5">

                <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">

                  Mật khẩu * <span className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 font-normal ml-1">(Bắt buộc)</span>

                </label>

                <div className="relative">

                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

                  <input 

                    type={showPassword ? "text" : "password"} 

                    name="password"

                    value={formData.password}

                    onChange={handleChange}

                    placeholder="Nhập 8 đến 128 ký tự" 

                    className={`w-full pl-10 pr-10 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${

                      fieldErrors.password

                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

                    }`}

                    disabled={loading}

                  />

                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 light:text-app-secondary hover:text-slate-600 light:hover:text-app-secondary dark:hover:text-slate-200 transition-colors">

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

                <label className="text-xs sm:text-sm font-medium text-slate-700 light:text-app-text dark:text-slate-300 block">Xác nhận lại mật khẩu</label>

                <div className="relative">

                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 light:text-app-secondary" />

                  <input 

                    type={showConfirmPassword ? "text" : "password"} 

                    name="confirm_password"

                    value={formData.confirm_password}

                    onChange={handleChange}

                    placeholder="Nhập lại mật khẩu vừa tạo" 

                    className={`w-full pl-10 pr-10 py-3 rounded-xl border text-sm transition-all focus:outline-none focus:ring-2 ${

                      fieldErrors.confirm_password

                        ? 'border-red-500 dark:border-red-500 bg-red-50/30 dark:bg-red-950/20 text-red-900 dark:text-red-100 focus:ring-red-500/20 focus:border-red-500'

                        : 'border-slate-200 light:border-app-border dark:border-slate-700/80 bg-slate-50/80 light:bg-app-page/80 dark:bg-slate-950/60 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary dark:placeholder:text-slate-500 focus:ring-blue-500/20 light:focus:ring-app-primary/20 focus:border-blue-500 light:focus:border-app-primary dark:focus:border-cyan-500/60'

                    }`}

                    disabled={loading}

                  />

                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 light:text-app-secondary hover:text-slate-600 light:hover:text-app-secondary dark:hover:text-slate-200 transition-colors">

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

            <label className="mb-4 block text-sm font-medium">Địa chỉ liên hệ (tùy chọn)<input name="address" maxLength={500} value={formData.address} onChange={e => setFormData(d => ({ ...d, address: e.target.value }))} className="mt-2 block w-full rounded-xl border p-3" /></label>
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

                className={`mt-1 rounded bg-white light:bg-app-surface dark:bg-slate-950 text-blue-600 light:text-app-primary focus:ring-blue-500/20 light:focus:ring-app-primary/20 cursor-pointer ${

                  fieldErrors.agreeTerms ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 light:border-app-border dark:border-slate-700'

                }`}

              />

              <span className="text-xs sm:text-sm text-slate-600 light:text-app-secondary dark:text-slate-400">

                Tôi đồng ý với <a href="#" className="text-blue-600 light:text-app-primary dark:text-cyan-400 font-semibold hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-blue-600 light:text-app-primary dark:text-cyan-400 font-semibold hover:underline">Chính sách bảo mật dữ liệu y tế</a> của VCare+.

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

              <TypewriterLoader />

            ) : (

              <>

                <span>Tạo tài khoản ngay</span>

                <ArrowRight className="w-5 h-5" />

              </>

            )}

          </button>

        </form>



        <div className="mt-8 text-center text-xs sm:text-sm">

          <span className="text-slate-600 light:text-app-secondary dark:text-slate-400">Đã có tài khoản? </span>

          <Link to="/login" className="font-semibold text-blue-600 light:text-app-primary dark:text-cyan-400 hover:text-blue-700 light:hover:text-app-primary dark:hover:text-cyan-300">

            Đăng nhập

          </Link>

        </div>

      </div>

    </div>

  )

}

