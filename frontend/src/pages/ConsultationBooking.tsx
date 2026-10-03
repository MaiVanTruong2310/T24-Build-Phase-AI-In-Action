import { TypewriterLoader } from '../components/TypewriterLoader';
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from '../app/store'
import {
  fetchDoctorConsultationService,
  fetchDoctors,
  fetchFacilities,
  fetchServiceCategories,
  fetchServices,
  fetchSpecialties,
  createPackageRequest,
  fetchMyPackageRequests,
} from '../features/appointment-booking/api'
import type {
  Doctor,
  Facility,
  MedicalService,
  PackageRequest,
  Specialty,
} from '../features/appointment-booking/api'
import {
  cancelConsultationRequest,
  createConsultationRequest,
  fetchMyRequests,
  fetchSessions,
} from '../features/coordination/api'
import type { ConsultationRequest, SessionSummary } from '../features/coordination/api'

const today = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const periodText = (period: string) => (period === 'morning' ? 'Buổi sáng' : 'Buổi chiều')

const formatCurrency = (val?: number | null) => {
  if (val == null || val === 0) return 'Liên hệ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val)
}

export default function ConsultationBooking() {
  const preset = useRef(new URLSearchParams(window.location.search))
  const navigate = useNavigate()
  const user = useSelector((state: RootState) => state.auth.user)

  // Mode: Khám Bác sĩ vs Khám Gói Dịch Vụ
  const [bookingMode, setBookingMode] = useState<'doctor' | 'package'>(() => {
    return preset.current.get('mode') === 'package' ? 'package' : 'doctor'
  })

  // Catalog chung
  const [allFacilities, setAllFacilities] = useState<Facility[]>([])
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [loadingFacilities, setLoadingFacilities] = useState(false)

  // =================== STATE CHO KHÁM BÁC SĨ (MODE DOCTOR) ===================
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [specialtyId, setSpecialtyId] = useState(() => preset.current.get('specialtyId') || '')
  const [facilityId, setFacilityId] = useState(() => preset.current.get('specialtyId') ? preset.current.get('facilityId') || '' : '')
  const [doctorId, setDoctorId] = useState(() => preset.current.get('doctorId') || '')
  const [doctorService, setDoctorService] = useState<MedicalService | null>(null)
  const pairRef = useRef(`${specialtyId}:${facilityId}`)
  const [date, setDate] = useState(today)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [selectedSession, setSelectedSession] = useState('')
  const [reason, setReason] = useState('')
  const [patientNote, setPatientNote] = useState('')
  const [loadingDoctors, setLoadingDoctors] = useState(false)
  const [suggestedFacilities, setSuggestedFacilities] = useState<Array<{ id: string; name: string; count: number }>>([])
  const [requests, setRequests] = useState<ConsultationRequest[]>([])

  // =================== STATE CHO GÓI KHÁM BỆNH (MODE PACKAGE) ===================
  const [packages, setPackages] = useState<MedicalService[]>([])
  const [packageCategories, setPackageCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('Tất cả')
  const [packageSearch, setPackageSearch] = useState<string>('')
  const [selectedPackage, setSelectedPackage] = useState<MedicalService | null>(null)
  const [packageFacilityId, setPackageFacilityId] = useState<string>('')
  const [packageDate, setPackageDate] = useState<string>(today)
  const [packagePeriod, setPackagePeriod] = useState<'morning' | 'afternoon'>('morning')
  const [packageNote, setPackageNote] = useState<string>('')
  const [myPackageRequests, setMyPackageRequests] = useState<PackageRequest[]>([])
  const [loadingPackages, setLoadingPackages] = useState(false)
  const [packageSubmitted, setPackageSubmitted] = useState<PackageRequest | null>(null)

  // =================== THÔNG TIN BỆNH NHÂN (DÀNH CHO KHÁCH CHƯA ĐĂNG NHẬP) ===================
  const [patientName, setPatientName] = useState('')
  const [patientPhone, setPatientPhone] = useState('')
  const [patientEmail, setPatientEmail] = useState('')
  const [gender, setGender] = useState<'male' | 'female' | 'other' | ''>('')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [guestSubmitted, setGuestSubmitted] = useState<ConsultationRequest | null>(null)

  // Common UI State
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // 1. Khởi tạo Catalog chung & Dịch vụ khám chuyên khoa mặc định
  useEffect(() => {
    void Promise.all([fetchSpecialties(), fetchFacilities(), fetchDoctorConsultationService()])
      .then(([s, f, ds]) => {
        setAllFacilities(f)
        setSpecialties(s)
        if (ds) setDoctorService(ds)
      })
      .catch(() => setError('Không thể tải danh mục khám.'))

    if (user) {
      void fetchMyRequests().then(setRequests).catch(() => undefined)
      void fetchMyPackageRequests().then(setMyPackageRequests).catch(() => undefined)
    }
  }, [user])

  // 2. Khởi tạo danh mục và danh sách Gói khám
  useEffect(() => {
    void fetchServiceCategories().then(setPackageCategories).catch(() => undefined)
  }, [])

  useEffect(() => {
    let active = true
    setLoadingPackages(true)
    const categoryParam = selectedCategory !== 'Tất cả' ? selectedCategory : undefined
    void fetchServices({ category: categoryParam, name: packageSearch.trim() || undefined, limit: 120 })
      .then((items) => {
        if (active) {
          // Lọc bỏ dịch vụ khám chuyên khoa lẻ để chỉ hiển thị các gói
          const onlyPackages = items.filter((x) => x.code !== 'DV-KHAN-CHUYEN-KHOA')
          setPackages(onlyPackages)
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoadingPackages(false)
      })
    return () => {
      active = false
    }
  }, [selectedCategory, packageSearch])

  // Chọn chuyên môn trước, sau đó tải các cơ sở phù hợp.
  useEffect(() => {
    let active = true
    setFacilities([])
    if (!specialtyId) {
      setLoadingFacilities(false)
      return
    }
    setLoadingFacilities(true)
    void fetchFacilities({ specialtyId })
      .then((items) => {
        if (!active) return
        setFacilities(items)
        setFacilityId((previous) => (items.some((item) => item.id === previous) ? previous : ''))
      })
      .catch(() => {
        if (active) setError('Không thể tải cơ sở khám phù hợp. Vui lòng chọn lại chuyên môn.')
      })
      .finally(() => {
        if (active) setLoadingFacilities(false)
      })
    return () => {
      active = false
    }
  }, [specialtyId])

  // 5. Tải danh sách Bác sĩ khi đã chọn Chuyên khoa & Cơ sở
  useEffect(() => {
    const pair = `${specialtyId}:${facilityId}`
    const pairChanged = pairRef.current !== pair
    pairRef.current = pair
    setSessions([])
    setSelectedSession('')
    if (pairChanged) {
      setDoctors([])
      setDoctorId('')
      setSuggestedFacilities([])
    }
    if (!specialtyId || !facilityId) {
      setLoadingDoctors(false)
      return
    }
    let active = true
    setLoadingDoctors(true)
    void fetchDoctors({ specialtyId, facilityId, bookingEnabled: true, limit: 100 })
      .then(async (d) => {
        if (!active) return
        setDoctors(d)
        setDoctorId((previous) => (d.some((x) => x.id === previous) ? previous : ''))

        if (d.length === 0) {
          try {
            const allDocs = await fetchDoctors({ specialtyId, bookingEnabled: true, limit: 100 })
            if (active) {
              const facMap = new Map<string, number>()
              for (const doc of allDocs) {
                for (const df of doc.facilities || []) {
                  if (df.facility_id && df.facility_id !== facilityId) {
                    facMap.set(df.facility_id, (facMap.get(df.facility_id) || 0) + 1)
                  }
                }
              }
              const suggestions = facilities
                .filter((f) => facMap.has(f.id))
                .map((f) => ({ id: f.id, name: f.name, count: facMap.get(f.id) || 0 }))
                .sort((a, b) => b.count - a.count)
              setSuggestedFacilities(suggestions)
            }
          } catch {
            // Ignore suggestion errors
          }
        } else {
          setSuggestedFacilities([])
        }
      })
      .catch(() => {
        if (active) setError('Không thể tải danh sách bác sĩ.')
      })
      .finally(() => {
        if (active) setLoadingDoctors(false)
      })
    return () => {
      active = false
    }
  }, [specialtyId, facilityId, facilities])

  // 6. Tải các ca/buổi khám (Sessions) khi đã chọn Bác sĩ, Cơ sở, Ngày
  useEffect(() => {
    setSessions([])
    setSelectedSession('')
    if (!doctorId || !facilityId || !date) return
    let active = true
    setLoading(true)
    void fetchSessions(doctorId, date, facilityId)
      .then((value) => {
        if (active) setSessions(value)
      })
      .catch(() => {
        if (active) setError('Không thể tải các buổi khám trống của bác sĩ.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [doctorId, facilityId, date])

  // =================== XỬ LÝ GỬI FORM KHÁM BÁC SĨ ===================
  const submitDoctorBooking = async () => {
    if (!selectedSession || !specialtyId || !reason.trim()) {
      setError('Vui lòng chọn chuyên khoa, bác sĩ, buổi khám và nhập lý do khám.')
      return
    }

    if (!user) {
      if (!patientName.trim() || patientName.trim().length < 2) {
        setError('Vui lòng nhập họ và tên bệnh nhân (tối thiểu 2 ký tự).')
        return
      }
      const cleanPhone = patientPhone.replace(/[\s.()-]/g, '')
      if (!/^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$/.test(cleanPhone)) {
        setError('Vui lòng nhập số điện thoại hợp lệ (10 số theo chuẩn Việt Nam).')
        return
      }
      if (!gender) {
        setError('Vui lòng chọn giới tính của bệnh nhân.')
        return
      }
      if (!dateOfBirth) {
        setError('Vui lòng chọn ngày sinh của bệnh nhân.')
        return
      }
      if (dateOfBirth > today()) {
        setError('Ngày sinh không thể nằm trong tương lai.')
        return
      }
    }

    setBusy(true)
    setError('')
    setSuccess('')

    // Tự động gán service_id của dịch vụ Khám chuyên khoa tổng quát
    const effectiveServiceId = doctorService?.id || (await fetchDoctorConsultationService())?.id
    if (!effectiveServiceId) {
      setError('Hệ thống đang chuẩn bị danh mục khám, vui lòng thử lại sau giây lát.')
      setBusy(false)
      return
    }

    const payload: Record<string, unknown> = {
      session_id: selectedSession,
      service_id: effectiveServiceId,
      specialty_id: specialtyId,
      encounter_type: 'in_person',
      reason: reason.trim(),
      patient_note: patientNote.trim() || undefined,
    }

    if (!user) {
      payload.patient_name = patientName.trim()
      payload.patient_phone = patientPhone.trim()
      payload.patient_email = patientEmail.trim() || undefined
      payload.gender = gender
      payload.date_of_birth = dateOfBirth
    }

    try {
      const created = await createConsultationRequest(payload)
      if (!user) {
        setGuestSubmitted(created)
        setSuccess(
          `Đã gửi yêu cầu khám bác sĩ thành công! Mã yêu cầu: ${created.id.slice(0, 8).toUpperCase()}. Nhân viên điều phối sẽ liên hệ số điện thoại ${patientPhone} để xác nhận giờ khám cụ thể.`
        )
        setPatientName('')
        setPatientPhone('')
        setPatientEmail('')
        setGender('')
        setDateOfBirth('')
      } else {
        setSuccess('Đã gửi yêu cầu khám thành công. Nhân viên điều phối sẽ gọi lại để tư vấn và chốt giờ khám cụ thể.')
        const currentRequests = await fetchMyRequests()
        setRequests(currentRequests)
      }
      setSelectedSession('')
      setReason('')
      setPatientNote('')
      const currentSessions = await fetchSessions(doctorId, date, facilityId)
      setSessions(currentSessions)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không thể gửi yêu cầu khám.')
    } finally {
      setBusy(false)
    }
  }

  // =================== XỬ LÝ GỬI FORM ĐĂNG KÝ GÓI KHÁM ===================
  const submitPackageBooking = async () => {
    if (!selectedPackage) {
      setError('Vui lòng chọn một gói khám trước.')
      return
    }
    if (!packageFacilityId) {
      setError('Vui lòng chọn cơ sở bệnh viện thực hiện gói khám.')
      return
    }
    if (!packageDate) {
      setError('Vui lòng chọn ngày khám mong muốn.')
      return
    }

    if (!user) {
      if (!patientName.trim() || patientName.trim().length < 2) {
        setError('Vui lòng nhập họ và tên người khám (tối thiểu 2 ký tự).')
        return
      }
      const cleanPhone = patientPhone.replace(/[\s.()-]/g, '')
      if (!/^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$/.test(cleanPhone)) {
        setError('Vui lòng nhập số điện thoại hợp lệ (10 số theo chuẩn Việt Nam).')
        return
      }
      if (!gender) {
        setError('Vui lòng chọn giới tính.')
        return
      }
      if (!dateOfBirth) {
        setError('Vui lòng chọn ngày sinh.')
        return
      }
    }

    setBusy(true)
    setError('')
    setSuccess('')

    try {
      const created = await createPackageRequest({
        service_id: selectedPackage.id,
        facility_id: packageFacilityId,
        preferred_date: packageDate,
        preferred_period: packagePeriod,
        note: packageNote.trim() || undefined,
        patient_name: !user ? patientName.trim() : undefined,
        patient_phone: !user ? patientPhone.trim() : undefined,
        patient_email: !user ? patientEmail.trim() || undefined : undefined,
        gender: !user ? gender : undefined,
        date_of_birth: !user ? dateOfBirth : undefined,
      })

      setPackageSubmitted(created)
      setSuccess(
        `Đăng ký gói khám "${selectedPackage.name}" thành công! Mã yêu cầu: ${created.id.slice(0, 8).toUpperCase()}. Điều phối viên sẽ liên hệ để tư vấn lộ trình và xếp lịch.`
      )
      setSelectedPackage(null)
      setPackageNote('')
      if (user) {
        const pkgs = await fetchMyPackageRequests()
        setMyPackageRequests(pkgs)
      } else {
        setPatientName('')
        setPatientPhone('')
        setPatientEmail('')
        setGender('')
        setDateOfBirth('')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không thể gửi yêu cầu đăng ký gói khám.')
    } finally {
      setBusy(false)
    }
  }

  const cancelPendingDoctor = async (id: string) => {
    if (!window.confirm('Huỷ yêu cầu khám bác sĩ đang chờ điều phối?')) return
    setError('')
    try {
      await cancelConsultationRequest(id)
      setRequests(await fetchMyRequests())
      if (doctorId && facilityId) setSessions(await fetchSessions(doctorId, date, facilityId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không thể huỷ yêu cầu.')
    }
  }

  const selectedDoctor = doctors.find((x) => x.id === doctorId)

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-12">
      {/* HEADER BANNER */}
      <header className="rounded-3xl bg-gradient-to-r from-blue-950 light:from-app-primary-strong to-blue-700 light:to-app-primary-strong p-6 text-white md:p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-200 light:text-app-on-primary">VCare+ · Hệ thống Đặt lịch</p>
        <h1 className="mt-2 text-2xl font-bold md:text-3xl">Đặt lịch khám & Gói dịch vụ y tế</h1>
        <p className="mt-2 max-w-2xl text-sm text-blue-100 light:text-app-on-primary">
          Lựa chọn linh hoạt: Khám trực tiếp với Bác sĩ chuyên khoa theo lịch hẹn, hoặc đăng ký các Gói khám & Lộ trình chăm sóc sức khỏe toàn diện.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Link
            to="/patient/doctors"
            className="rounded-lg border border-blue-300/80 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10 light:hover:bg-app-surface/10"
          >
            Tìm hiểu đội ngũ bác sĩ →
          </Link>
          {!user && (
            <button
              type="button"
              onClick={() => navigate('/login?returnTo=/patient/appointments')}
              className="rounded-lg bg-white/15 light:bg-app-surface/15 px-4 py-2 text-sm font-medium text-blue-100 light:text-app-on-primary hover:bg-white/25 light:hover:bg-app-surface/25 transition cursor-pointer"
            >
              Đã có tài khoản? Đăng nhập ngay
            </button>
          )}
        </div>
      </header>

      {/* THANH CHUYỂN ĐỔI CHẾ ĐỘ: KHÁM BÁC SĨ vs GÓI KHÁM */}
      <div className="flex border border-slate-200 light:border-app-border bg-white light:bg-app-surface rounded-2xl p-1.5 shadow-sm">
        <button
          type="button"
          onClick={() => {
            setBookingMode('doctor')
            setError('')
            setSuccess('')
          }}
          className={`flex-1 py-3.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition cursor-pointer ${
            bookingMode === 'doctor'
              ? 'bg-blue-600 light:bg-app-primary text-white shadow-md'
              : 'text-slate-600 light:text-app-secondary hover:text-blue-600 light:hover:text-app-primary hover:bg-slate-50 light:hover:bg-app-page'
          }`}
        >
          <span className="text-base">🩺</span>
          <span>Khám Chuyên Khoa Cùng Bác Sĩ</span>
        </button>
        <button
          type="button"
          onClick={() => {
            setBookingMode('package')
            setError('')
            setSuccess('')
          }}
          className={`flex-1 py-3.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition cursor-pointer ${
            bookingMode === 'package'
              ? 'bg-blue-600 light:bg-app-primary text-white shadow-md'
              : 'text-slate-600 light:text-app-secondary hover:text-blue-600 light:hover:text-app-primary hover:bg-slate-50 light:hover:bg-app-page'
          }`}
        >
          <span className="text-base">🎁</span>
          <span>Gói Khám Bệnh & Lộ Trình Sức Khỏe</span>
          <span className="hidden sm:inline-block text-[11px] py-0.5 px-2 rounded-full bg-amber-400 text-slate-900 light:text-app-text font-extrabold ml-1">
            200+ Gói
          </span>
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
          {error}
        </p>
      )}
      {success && (
        <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800 space-y-1">
          <p className="font-semibold text-emerald-900">✓ Thao tác thành công</p>
          <p>{success}</p>
        </div>
      )}

      {/* ========================================================================= */}
      {/* CHẾ ĐỘ 1: KHÁM CHUYÊN KHOA VỚI BÁC SĨ                                     */}
      {/* ========================================================================= */}
      {bookingMode === 'doctor' && (
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <section className="space-y-6 rounded-3xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-5 shadow-sm md:p-7">
            {/* BƯỚC 1: THÔNG TIN KHÁM VÀ BÁC SĨ */}
            <div>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900 light:text-app-text">1. Chọn Chuyên môn & Bác sĩ</h2>
                <span className="rounded-full bg-blue-50 light:bg-app-muted border border-blue-200 light:border-app-border px-3 py-1 text-xs font-semibold text-blue-700 light:text-app-primary">
                  Dịch vụ: Khám Chuyên khoa (350.000 ₫)
                </span>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {/* CHỌN CHUYÊN MÔN KHÁM TRƯỚC */}
                <label className="text-sm font-semibold text-slate-700 light:text-app-text">
                  Chuyên môn / Lĩnh vực khám *
                  <select
                    className="mt-1.5 w-full rounded-xl border border-slate-300 light:border-app-border p-3 font-normal text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary focus:ring-1 focus:ring-blue-600 light:focus:ring-app-primary"
                    value={specialtyId}
                    onChange={(e) => {
                      setSpecialtyId(e.target.value)
                      setFacilityId('')
                      setDoctorId('')
                      setDoctors([])
                      setFacilities([])
                      setSessions([])
                      setSelectedSession('')
                    }}
                  >
                    <option value="">-- Chọn chuyên môn khám --</option>
                    {specialties.map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.name}
                      </option>
                    ))}
                  </select>
                </label>

                {/* CƠ SỞ CHỈ CHỌN ĐƯỢC SAU CHUYÊN MÔN */}
                <label className="text-sm font-semibold text-slate-700 light:text-app-text">
                  <div className="flex items-center justify-between">
                    <span>Cơ sở bệnh viện *</span>
                    {specialtyId && !loadingFacilities && (
                      <span className="text-xs font-normal text-blue-600 light:text-app-primary">
                        {facilities.length} cơ sở phù hợp
                      </span>
                    )}
                  </div>
                  <select
                    className="mt-1.5 w-full rounded-xl border border-slate-300 light:border-app-border p-3 font-normal text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary focus:ring-1 focus:ring-blue-600 light:focus:ring-app-primary disabled:cursor-not-allowed disabled:bg-slate-50 light:disabled:bg-app-page disabled:text-slate-400 light:disabled:text-app-secondary"
                    value={facilityId}
                    disabled={!specialtyId || loadingFacilities || facilities.length === 0}
                    onChange={(e) => setFacilityId(e.target.value)}
                  >
                    <option value="">
                      {!specialtyId
                        ? 'Chọn chuyên môn trước'
                        : loadingFacilities
                        ? 'Đang tải cơ sở phù hợp…'
                        : facilities.length === 0
                        ? 'Chưa có cơ sở phù hợp'
                        : '-- Chọn cơ sở bệnh viện --'}
                    </option>
                    {facilities.map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.name}
                      </option>
                    ))}
                  </select>
                </label>

                {/* CHỌN BÁC SĨ CHUYÊN KHOA */}
                <label className="text-sm font-semibold text-slate-700 light:text-app-text sm:col-span-2">
                  Bác sĩ chuyên khoa tiếp nhận *
                  <select
                    className="mt-1.5 w-full rounded-xl border border-slate-300 light:border-app-border p-3 font-normal text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary focus:ring-1 focus:ring-blue-600 light:focus:ring-app-primary disabled:bg-slate-50 light:disabled:bg-app-page disabled:text-slate-400 light:disabled:text-app-secondary"
                    value={doctorId}
                    onChange={(e) => setDoctorId(e.target.value)}
                    disabled={!specialtyId || !facilityId || loadingDoctors}
                  >
                    <option value="">
                      {loadingDoctors
                        ? 'Đang tìm bác sĩ phù hợp…'
                        : !specialtyId || !facilityId
                        ? 'Chọn chuyên môn và cơ sở trước'
                        : doctors.length === 0
                        ? 'Cơ sở này chưa có bác sĩ chuyên môn này'
                        : `Chọn bác sĩ (${doctors.length} bác sĩ có sẵn)`}
                    </option>
                    {doctors.map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.full_name} {x.title ? `(${x.title})` : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {/* GỢI Ý CƠ SỞ NẾU CHUYÊN KHOA ĐÃ CHỌN KHÔNG CÓ BÁC SĨ TẠI CƠ SỞ HIỆN TẠI */}
              {!loadingDoctors && specialtyId && facilityId && doctors.length === 0 && (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 shadow-sm">
                  <div className="flex items-start gap-3">
                    <span className="text-xl">⚠️</span>
                    <div className="space-y-2 flex-1">
                      <p className="font-semibold text-amber-950">
                        Cơ sở &ldquo;{facilities.find((f) => f.id === facilityId)?.name}&rdquo; hiện chưa có bác sĩ chuyên môn &ldquo;{specialties.find((s) => s.id === specialtyId)?.name}&rdquo;.
                      </p>
                      {suggestedFacilities.length > 0 ? (
                        <div>
                          <p className="text-xs text-amber-800 font-medium mb-2">
                            Chuyên môn này đang có bác sĩ tiếp nhận tại các cơ sở sau (bấm để chuyển ngay):
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {suggestedFacilities.map((sf) => (
                              <button
                                key={sf.id}
                                type="button"
                                onClick={() => setFacilityId(sf.id)}
                                className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-white light:bg-app-surface px-3 py-1.5 text-xs font-bold text-blue-700 light:text-app-primary shadow-sm transition hover:bg-blue-50 light:hover:bg-app-muted cursor-pointer"
                              >
                                🏥 {sf.name} ({sf.count} bác sĩ) →
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              )}

              {/* THẺ TÓM TẮT BÁC SĨ ĐÃ CHỌN */}
              {selectedDoctor && (
                <div className="mt-4 flex items-center gap-3.5 rounded-2xl border border-blue-200 light:border-app-border bg-blue-50/80 light:bg-app-muted/80 p-4 shadow-sm">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-600 light:bg-app-primary font-bold text-white shadow-sm">
                    {selectedDoctor.full_name.split(' ').slice(-1)[0]?.charAt(0) || 'BS'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-slate-900 light:text-app-text">{selectedDoctor.full_name}</p>
                      <span className="rounded-full bg-blue-200/80 light:bg-app-tint/80 px-2.5 py-0.5 text-[11px] font-semibold text-blue-900 light:text-app-primary-strong">
                        {selectedDoctor.title || 'Bác sĩ chuyên khoa'}
                      </span>
                    </div>
                    <p className="truncate text-xs text-slate-600 light:text-app-secondary mt-1">
                      {[
                        selectedDoctor.position,
                        selectedDoctor.facilities?.find((df) => df.facility_id === facilityId)?.department,
                        selectedDoctor.experience_years ? `${selectedDoctor.experience_years} năm kinh nghiệm` : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* BƯỚC 2: CHỌN NGÀY VÀ BUỔI KHÁM */}
            <div className="border-t border-slate-200 light:border-app-border pt-5">
              <h2 className="text-lg font-bold text-slate-900 light:text-app-text">2. Chọn ngày & buổi khám</h2>
              <div className="mt-3">
                <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
                  Ngày khám mong muốn
                  <input
                    type="date"
                    min={today()}
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="mt-1.5 block w-full rounded-xl border border-slate-300 light:border-app-border p-3 text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary sm:w-64"
                  />
                </label>
              </div>

              <div className="mt-4">
                {loading ? (
                  <div role="status" className="flex items-center gap-3 text-sm text-slate-500 light:text-app-secondary"><TypewriterLoader size="md" />Đang tải các buổi khám trống…</div>
                ) : doctorId && sessions.length === 0 ? (
                  <p className="rounded-xl bg-slate-50 light:bg-app-page p-4 text-sm text-slate-600 light:text-app-secondary">
                    Chưa có buổi khám được công bố trong ngày này. Vui lòng chọn ngày khác hoặc bác sĩ khác.
                  </p>
                ) : null}

                <div className="grid gap-3 sm:grid-cols-2">
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      disabled={session.remaining === 0}
                      onClick={() => setSelectedSession(session.id)}
                      className={`rounded-2xl border p-4 text-left transition cursor-pointer ${
                        selectedSession === session.id
                          ? 'border-blue-600 light:border-app-primary bg-blue-50/80 light:bg-app-muted/80 ring-2 ring-blue-500/20 light:ring-app-primary/20'
                          : 'border-slate-200 light:border-app-border hover:border-blue-300'
                      } disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      <strong className="block text-base text-slate-900 light:text-app-text">{periodText(session.period)}</strong>
                      <span className="mt-1 block text-xs text-slate-600 light:text-app-secondary">
                        Còn nhận {session.remaining}/{session.capacity} yêu cầu
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* BƯỚC 3: THÔNG TIN NGƯỜI ĐẶT KHÁM */}
            <div className="border-t border-slate-200 light:border-app-border pt-5">
              <h2 className="text-lg font-bold text-slate-900 light:text-app-text">3. Thông tin người đặt khám</h2>

              {user ? (
                <div className="mt-3 rounded-2xl border border-blue-200 light:border-app-border bg-blue-50/60 light:bg-app-muted/60 p-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-blue-900 light:text-app-primary-strong flex items-center gap-1.5">
                      <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
                      Hồ sơ tài khoản đã xác thực
                    </span>
                    <span className="text-xs text-blue-700 light:text-app-primary">Tài khoản thành viên</span>
                  </div>
                  <div className="mt-2 text-slate-700 light:text-app-text">
                    <p>
                      Họ và tên: <strong className="text-slate-900 light:text-app-text">{user.full_name || 'Bệnh nhân'}</strong>
                    </p>
                    <p className="mt-0.5">
                      Số điện thoại: <strong className="text-slate-900 light:text-app-text">{user.phone || 'Chưa cập nhật'}</strong>
                      {user.email && <span className="ml-3 text-slate-500 light:text-app-secondary">Email: {user.email}</span>}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-3 space-y-4 rounded-2xl border border-blue-200/90 light:border-app-border/90 bg-blue-50/50 light:bg-app-muted/50 p-4">
                  <div className="flex items-start justify-between gap-2 border-b border-blue-200/60 light:border-app-border/60 pb-2">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-blue-800 light:text-app-primary-strong">
                        Dành cho khách chưa đăng nhập
                      </span>
                      <p className="text-xs text-slate-600 light:text-app-secondary mt-0.5">
                        Vui lòng điền thông tin cá nhân để điều phối viên tạo hồ sơ khám và gọi lại xác nhận.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate('/login?returnTo=/patient/appointments')}
                      className="shrink-0 text-xs font-semibold text-blue-700 light:text-app-primary underline hover:text-blue-800 light:hover:text-app-primary-strong cursor-pointer"
                    >
                      Đăng nhập
                    </button>
                  </div>

                  <div className="grid gap-3.5 sm:grid-cols-2">
                    <label className="text-xs font-semibold text-slate-700 light:text-app-text sm:col-span-2">
                      Họ và tên bệnh nhân *
                      <input
                        type="text"
                        required
                        placeholder="Ví dụ: Nguyễn Văn An"
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />
                    </label>

                    <label className="text-xs font-semibold text-slate-700 light:text-app-text">
                      Số điện thoại liên hệ *
                      <input
                        type="tel"
                        required
                        placeholder="Ví dụ: 0912345678"
                        value={patientPhone}
                        onChange={(e) => setPatientPhone(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />
                    </label>

                    <label className="text-xs font-semibold text-slate-700 light:text-app-text">
                      Email nhận thông tin (tuỳ chọn)
                      <input
                        type="email"
                        placeholder="Ví dụ: an.nguyen@example.com"
                        value={patientEmail}
                        onChange={(e) => setPatientEmail(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />
                    </label>

                    <label className="text-xs font-semibold text-slate-700 light:text-app-text">
                      Giới tính *
                      <select
                        value={gender}
                        onChange={(e) => setGender(e.target.value as 'male' | 'female' | 'other' | '')}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      >
                        <option value="">Chọn giới tính</option>
                        <option value="male">Nam</option>
                        <option value="female">Nữ</option>
                        <option value="other">Khác</option>
                      </select>
                    </label>

                    <label className="text-xs font-semibold text-slate-700 light:text-app-text">
                      Ngày sinh *
                      <input
                        type="date"
                        max={today()}
                        value={dateOfBirth}
                        onChange={(e) => setDateOfBirth(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border bg-white light:bg-app-surface p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />
                    </label>
                  </div>
                </div>
              )}
            </div>

            {/* BƯỚC 4: LÝ DO KHÁM & GỬI YÊU CẦU */}
            <div className="border-t border-slate-200 light:border-app-border pt-5">
              <h2 className="text-lg font-bold text-slate-900 light:text-app-text">4. Nội dung & Lý do khám</h2>
              <div className="mt-3 space-y-3.5">
                <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
                  Mô tả lý do khám / Triệu chứng gặp phải *
                  <textarea
                    className="mt-1.5 w-full rounded-xl border border-slate-300 light:border-app-border p-3 font-normal text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                    rows={3}
                    placeholder="Ví dụ: Đau tức ngực trái 2 ngày nay, hơi khó thở khi gắng sức..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>

                <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
                  Ghi chú thêm (khung giờ gọi lại thuận tiện, lưu ý đặc biệt)
                  <textarea
                    className="mt-1.5 w-full rounded-xl border border-slate-300 light:border-app-border p-3 font-normal text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                    rows={2}
                    placeholder="Ví dụ: Vui lòng gọi lại sau 17h chiều..."
                    value={patientNote}
                    onChange={(e) => setPatientNote(e.target.value)}
                  />
                </label>

                <div className="pt-2">
                  <button
                    type="button"
                    disabled={busy || !selectedSession}
                    onClick={() => void submitDoctorBooking()}
                    className="w-full sm:w-auto rounded-xl bg-blue-700 light:bg-app-primary-hover px-7 py-3.5 font-semibold text-white shadow-md shadow-blue-700/25 light:shadow-app-primary/25 transition hover:bg-blue-800 light:hover:bg-app-primary-hover disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {busy ? 'Đang gửi thông tin…' : 'Gửi yêu cầu khám với Bác sĩ'}
                  </button>
                  <p className="mt-2 text-xs text-slate-500 light:text-app-secondary">
                    ℹ️ Lưu ý: Điều phối viên sẽ gọi điện xác minh và chốt giờ khám cụ thể theo yêu cầu của bạn.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* SIDEBAR: YÊU CẦU GẦN ĐÂY */}
          <aside className="space-y-5">
            {guestSubmitted && (
              <div className="rounded-3xl border border-emerald-200 bg-emerald-50/80 p-5 shadow-sm text-sm">
                <div className="flex items-center gap-1.5 text-emerald-900 font-bold">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-600" />
                  <span>Yêu cầu khám vừa tạo</span>
                </div>
                <div className="mt-3 space-y-1.5 text-xs text-emerald-950">
                  <p>
                    Mã yêu cầu: <strong className="font-mono text-emerald-800">{guestSubmitted.id.slice(0, 8).toUpperCase()}</strong>
                  </p>
                  <p>
                    Buổi khám:{' '}
                    <strong>
                      {guestSubmitted.date} ({periodText(guestSubmitted.period)})
                    </strong>
                  </p>
                  <p>
                    Trạng thái:{' '}
                    <span className="rounded bg-emerald-200/70 px-1.5 py-0.5 font-semibold text-emerald-800">
                      Chờ nhân viên liên hệ
                    </span>
                  </p>
                </div>
              </div>
            )}

            {user ? (
              <div className="rounded-3xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-5 shadow-sm">
                <h2 className="font-bold text-slate-900 light:text-app-text text-base">Yêu cầu khám bác sĩ của bạn</h2>
                <div className="mt-4 space-y-3">
                  {requests.length === 0 && (
                    <p className="text-xs text-slate-500 light:text-app-secondary">Bạn chưa gửi yêu cầu khám nào gần đây.</p>
                  )}
                  {requests.slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-xl border border-slate-100 light:border-app-border bg-slate-50/50 light:bg-app-page/50 p-3 text-xs space-y-1">
                      <div className="flex justify-between items-start gap-2">
                        <strong className="text-slate-900 light:text-app-text">
                          {item.date} · {periodText(item.period)}
                        </strong>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            item.status === 'pending'
                              ? 'bg-amber-100 text-amber-800'
                              : item.status === 'confirmed'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 light:bg-app-tint text-slate-700 light:text-app-text'
                          }`}
                        >
                          {item.status === 'pending' ? 'Chờ gọi lại' : item.status === 'confirmed' ? 'Đã chốt lịch' : 'Đã đóng'}
                        </span>
                      </div>
                      {item.starts_at && (
                        <p className="text-slate-600 light:text-app-secondary">
                          Giờ khám: {new Date(item.starts_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      )}
                      {item.staff_note && <p className="text-slate-500 light:text-app-secondary italic">Ghi chú: {item.staff_note}</p>}
                      {item.status === 'pending' && (
                        <button
                          type="button"
                          onClick={() => void cancelPendingDoctor(item.id)}
                          className="mt-1 text-[11px] font-semibold text-red-600 hover:text-red-700 cursor-pointer"
                        >
                          Huỷ yêu cầu
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-blue-100 light:border-app-border bg-gradient-to-br from-blue-50/80 light:from-app-muted/80 to-white p-5 shadow-sm text-xs space-y-3">
                <h2 className="font-bold text-slate-900 light:text-app-text text-sm">💡 Lợi ích khi đăng nhập tài khoản</h2>
                <ul className="space-y-2 text-slate-600 light:text-app-secondary">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600 light:text-app-primary font-bold">✓</span>
                    <span>Tự động lưu hồ sơ bệnh án và lịch sử thăm khám trọn đời.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600 light:text-app-primary font-bold">✓</span>
                    <span>Theo dõi trạng thái điều phối và nhận thông báo nhắc lịch tự động.</span>
                  </li>
                </ul>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* ========================================================================= */}
      {/* CHẾ ĐỘ 2: GÓI KHÁM BỆNH & LỘ TRÌNH SỨC KHỎE                                */}
      {/* ========================================================================= */}
      {bookingMode === 'package' && (
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <section className="space-y-6">
            {/* BỘ LỌC DANH MỤC & TÌM KIẾM GÓI */}
            <div className="rounded-3xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-5 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 light:text-app-text">Danh mục gói dịch vụ & lộ trình khám</h2>
                  <p className="text-xs text-slate-500 light:text-app-secondary">Chọn gói khám định sẵn để được chăm sóc toàn diện theo quy trình chuẩn.</p>
                </div>
                <div className="relative w-full sm:w-64">
                  <input
                    type="text"
                    placeholder="Tìm tên gói khám…"
                    value={packageSearch}
                    onChange={(e) => setPackageSearch(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 light:border-app-border px-3.5 py-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary focus:ring-1 focus:ring-blue-600 light:focus:ring-app-primary"
                  />
                  {packageSearch && (
                    <button
                      type="button"
                      onClick={() => setPackageSearch('')}
                      className="absolute right-2.5 top-2 text-xs text-slate-400 light:text-app-secondary hover:text-slate-600 light:hover:text-app-secondary cursor-pointer"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>

              {/* PILLS CATEGORY */}
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedCategory('Tất cả')}
                  className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                    selectedCategory === 'Tất cả'
                      ? 'bg-blue-600 light:bg-app-primary text-white shadow-sm'
                      : 'bg-slate-100 light:bg-app-muted text-slate-700 light:text-app-text hover:bg-slate-200 light:hover:bg-app-tint'
                  }`}
                >
                  Tất cả ({packages.length})
                </button>
                {packageCategories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                      selectedCategory === cat
                        ? 'bg-blue-600 light:bg-app-primary text-white shadow-sm'
                        : 'bg-slate-100 light:bg-app-muted text-slate-700 light:text-app-text hover:bg-slate-200 light:hover:bg-app-tint'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* DANH SÁCH CÁC GÓI KHÁM */}
            <div className="space-y-4">
              {loadingPackages ? (
                <div className="rounded-3xl border bg-white light:bg-app-surface p-12 text-center text-sm text-slate-500 light:text-app-secondary">
                  <TypewriterLoader size="md" />
                  Đang tải danh sách các gói khám…
                </div>
              ) : packages.length === 0 ? (
                <div className="rounded-3xl border bg-white light:bg-app-surface p-12 text-center text-sm text-slate-500 light:text-app-secondary">
                  Không tìm thấy gói khám phù hợp với từ khóa này.
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {packages.map((pkg) => {
                    const isSelected = selectedPackage?.id === pkg.id
                    return (
                      <article
                        key={pkg.id}
                        className={`flex flex-col justify-between rounded-2xl border bg-white light:bg-app-surface p-5 transition shadow-sm ${
                          isSelected
                            ? 'border-blue-600 light:border-app-primary ring-2 ring-blue-500/20 light:ring-app-primary/20 bg-blue-50/30 light:bg-app-muted/30'
                            : 'border-slate-200 light:border-app-border hover:border-blue-300 hover:shadow-md'
                        }`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <span className="rounded-full bg-blue-50 light:bg-app-muted px-2.5 py-0.5 text-[11px] font-semibold text-blue-700 light:text-app-primary border border-blue-100 light:border-app-border">
                              {pkg.category || 'Gói chăm sóc'}
                            </span>
                            {pkg.duration_minutes ? (
                              <span className="text-[11px] text-slate-400 light:text-app-secondary font-medium">
                                ⏱ {pkg.duration_minutes} phút
                              </span>
                            ) : null}
                          </div>

                          <h3 className="mt-2.5 font-bold text-slate-900 light:text-app-text text-base leading-snug line-clamp-2">
                            {pkg.name}
                          </h3>

                          {pkg.description ? (
                            <p className="mt-1.5 text-xs text-slate-600 light:text-app-secondary line-clamp-2 leading-relaxed">
                              {pkg.description}
                            </p>
                          ) : null}
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-100 light:border-app-border flex items-center justify-between">
                          <div>
                            <span className="text-[10px] text-slate-400 light:text-app-secondary uppercase font-semibold block">Chi phí gói</span>
                            <span className="text-base font-extrabold text-blue-700 light:text-app-primary">
                              {formatCurrency(pkg.price)}
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setSelectedPackage(pkg)
                              if (!packageFacilityId && allFacilities[0]) {
                                setPackageFacilityId(allFacilities[0].id)
                              }
                              window.scrollTo({ top: 350, behavior: 'smooth' })
                            }}
                            className={`rounded-xl px-4 py-2 text-xs font-bold transition cursor-pointer ${
                              isSelected
                                ? 'bg-blue-600 light:bg-app-primary text-white'
                                : 'bg-blue-50 light:bg-app-muted text-blue-700 light:text-app-primary hover:bg-blue-600 light:hover:bg-app-primary-hover hover:text-white'
                            }`}
                          >
                            {isSelected ? '✓ Đang chọn' : 'Đăng ký gói →'}
                          </button>
                        </div>
                      </article>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          {/* FORM ĐĂNG KÝ GÓI KHÁM ĐÃ CHỌN (SIDEBAR HOẶC PANEL) */}
          <aside className="space-y-5">
            <div className="rounded-3xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-5 shadow-sm sticky top-20">
              <h2 className="font-bold text-slate-900 light:text-app-text text-base flex items-center gap-2">
                <span>📋</span>
                <span>Thông tin đăng ký gói</span>
              </h2>

              {selectedPackage ? (
                <div className="mt-3.5 space-y-4">
                  {/* TÓM TẮT GÓI ĐÃ CHỌN */}
                  <div className="rounded-2xl border border-blue-200 light:border-app-border bg-blue-50/70 light:bg-app-muted/70 p-3.5 text-xs space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 light:text-app-primary">
                      Gói dịch vụ đã chọn
                    </span>
                    <p className="font-bold text-slate-900 light:text-app-text text-sm">{selectedPackage.name}</p>
                    <p className="text-blue-800 light:text-app-primary-strong font-extrabold text-base">
                      {formatCurrency(selectedPackage.price)}
                    </p>
                  </div>

                  {/* CHỌN CƠ SỞ BỆNH VIỆN TIẾP NHẬN */}
                  <label className="block text-xs font-semibold text-slate-700 light:text-app-text">
                    Cơ sở bệnh viện tiếp nhận *
                    <select
                      value={packageFacilityId}
                      onChange={(e) => setPackageFacilityId(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border p-2.5 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                    >
                      <option value="">-- Chọn cơ sở bệnh viện --</option>
                      {allFacilities.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  {/* CHỌN NGÀY & BUỔI DỰ KIẾN */}
                  <div className="grid grid-cols-2 gap-2.5">
                    <label className="block text-xs font-semibold text-slate-700 light:text-app-text">
                      Ngày dự kiến *
                      <input
                        type="date"
                        min={today()}
                        value={packageDate}
                        onChange={(e) => setPackageDate(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />
                    </label>

                    <label className="block text-xs font-semibold text-slate-700 light:text-app-text">
                      Buổi mong muốn *
                      <select
                        value={packagePeriod}
                        onChange={(e) => setPackagePeriod(e.target.value as 'morning' | 'afternoon')}
                        className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      >
                        <option value="morning">Buổi sáng</option>
                        <option value="afternoon">Buổi chiều</option>
                      </select>
                    </label>
                  </div>

                  {/* THÔNG TIN NGƯỜI ĐĂNG KÝ (NẾU CHƯA ĐĂNG NHẬP) */}
                  {!user && (
                    <div className="space-y-2.5 border-t border-slate-100 light:border-app-border pt-3">
                      <span className="text-[11px] font-bold text-slate-800 light:text-app-text uppercase">Thông tin liên hệ người khám</span>

                      <input
                        type="text"
                        placeholder="Họ và tên người khám *"
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />

                      <input
                        type="tel"
                        placeholder="Số điện thoại liên hệ *"
                        value={patientPhone}
                        onChange={(e) => setPatientPhone(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                      />

                      <div className="grid grid-cols-2 gap-2">
                        <select
                          value={gender}
                          onChange={(e) => setGender(e.target.value as 'male' | 'female' | 'other' | '')}
                          className="rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                        >
                          <option value="">Giới tính *</option>
                          <option value="male">Nam</option>
                          <option value="female">Nữ</option>
                        </select>

                        <input
                          type="date"
                          max={today()}
                          value={dateOfBirth}
                          onChange={(e) => setDateOfBirth(e.target.value)}
                          className="rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                        />
                      </div>
                    </div>
                  )}

                  {/* GHI CHÚ NHU CẦU */}
                  <label className="block text-xs font-semibold text-slate-700 light:text-app-text">
                    Ghi chú nhu cầu / Tình trạng sức khỏe
                    <textarea
                      rows={2}
                      placeholder="Ví dụ: Mong muốn tư vấn thêm về gói hoặc có người cao tuổi đi cùng..."
                      value={packageNote}
                      onChange={(e) => setPackageNote(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-300 light:border-app-border p-2 text-xs text-slate-900 light:text-app-text outline-none focus:border-blue-600 light:focus:border-app-primary"
                    />
                  </label>

                  <button
                    type="button"
                    disabled={busy || !packageFacilityId}
                    onClick={() => void submitPackageBooking()}
                    className="w-full rounded-xl bg-blue-700 light:bg-app-primary-hover py-3 font-semibold text-white shadow-md shadow-blue-700/25 light:shadow-app-primary/25 transition hover:bg-blue-800 light:hover:bg-app-primary-hover disabled:opacity-50 cursor-pointer"
                  >
                    {busy ? 'Đang gửi đăng ký…' : 'Xác nhận đăng ký gói khám'}
                  </button>
                </div>
              ) : (
                <div className="mt-4 rounded-2xl bg-slate-50 light:bg-app-page border border-dashed border-slate-200 light:border-app-border p-6 text-center text-xs text-slate-500 light:text-app-secondary">
                  <span className="text-2xl block mb-2">👈</span>
                  Vui lòng bấm <strong>&ldquo;Đăng ký gói →&rdquo;</strong> ở một gói khám bất kỳ bên trái để bắt đầu.
                </div>
              )}
            </div>

            {/* DANH SÁCH YÊU CẦU GÓI CỦA TÔI NẾU ĐÃ ĐĂNG NHẬP */}
            {user && myPackageRequests.length > 0 && (
              <div className="rounded-3xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-5 shadow-sm">
                <h3 className="font-bold text-slate-900 light:text-app-text text-sm">Gói khám bạn đã đăng ký</h3>
                <div className="mt-3 space-y-2.5">
                  {myPackageRequests.slice(0, 4).map((pr) => (
                    <div key={pr.id} className="rounded-xl border border-slate-100 light:border-app-border bg-slate-50/60 light:bg-app-page/60 p-3 text-xs space-y-1">
                      <div className="flex justify-between items-start gap-1">
                        <strong className="text-slate-900 light:text-app-text line-clamp-1">{pr.service_name}</strong>
                        <span className="rounded bg-blue-100 light:bg-app-tint text-blue-800 light:text-app-primary-strong px-1.5 py-0.5 text-[10px] font-semibold shrink-0">
                          {pr.status === 'pending' ? 'Chờ liên hệ' : pr.status}
                        </span>
                      </div>
                      <p className="text-slate-500 light:text-app-secondary text-[11px]">
                        🏥 {pr.facility_name} · Ngày: {pr.preferred_date}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}
