import type { PatientProfile } from '../patient-profiles/api';
import { appointmentDateError, birthDateError, formatDateVN, latestAppointmentDate } from '../appointment-booking/dateValidation';
import { DateInputVN } from '../../components/DateInputVN';
import { TypewriterLoader } from '../../components/TypewriterLoader';
import { memo, useState, useEffect, useMemo, useRef, type FormEvent } from 'react';
import { useSelector } from 'react-redux';
import type { RootState } from '../../app/store';
import { Calendar, CheckCircle2, Clock, Hospital, MapPin, Phone, Sparkles, Stethoscope, User, X, ShieldCheck, AlertCircle, Package, Search, Filter, Check, ChevronRight, Info, GripVertical, ArrowUp, ArrowDown, Plus, Trash2 } from 'lucide-react';
import { submitBooking, type BookingIntake } from './api';
import {
  fetchServices,
  fetchFacilities,
  type Facility,
  fetchServiceCategories,
  createPackageRequest,
  type MedicalService,
} from '../appointment-booking/api';

interface LiveBookingPanelProps {
  intake?: BookingIntake | null;
  patientProfileId?: string;
  selectedPatient?: PatientProfile;
  sessionId: string;
  isMobileDrawer?: boolean;
  onClose?: () => void;
  onSubmitted?: (requestCode: string) => void;
}

const VINMEC_FACILITIES = [
  'Bệnh viện ĐKQT Vinmec Times City (Hà Nội)',
  'Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)',
  'Bệnh viện ĐKQT Vinmec Ocean Park 2 (Hưng Yên)',
  'Phòng khám ĐKQT Vinmec Smart City (Hà Nội)',
  'Phòng khám ĐKQT Vinmec Royal City (Hà Nội)',
  'Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)',
  'Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)',
  'Bệnh viện ĐKQT Vinmec Hải Phòng',
  'Bệnh viện ĐKQT Vinmec Đà Nẵng',
  'Bệnh viện ĐKQT Vinmec Nha Trang',
  'Bệnh viện ĐKQT Vinmec Phú Quốc',
  'Bệnh viện ĐKQT Vinmec Hạ Long',
  'Bệnh viện ĐKQT Vinmec Cần Thơ',
];

const VINMEC_SPECIALTIES = [
  'Khoa Thần kinh',
  'Khoa Tiêu hóa - Gan mật',
  'Trung tâm Tim mạch',
  'Khoa Nội hô hấp',
  'Khoa Chấn thương chỉnh hình & Cột sống',
  'Khoa Cơ xương khớp',
  'Khoa Tai - Mũi - Họng',
  'Khoa Thận - Tiết niệu',
  'Khoa Nội tiết - Đái tháo đường',
  'Khoa Nhi',
  'Khoa Sản phụ khoa',
  'Khoa Mắt',
  'Khoa Da liễu',
  'Khoa Răng - Hàm - Mặt',
  'Trung tâm Ung bướu',
  'Khoa Miễn dịch - Dị ứng',
  'Khoa Truyền nhiễm',
  'Khoa Sức khỏe tổng quát',
  'Khoa Cấp cứu',
];

const getSpecialtyOptions = (currentVal: string) => {
  if (currentVal && !VINMEC_SPECIALTIES.includes(currentVal)) {
    return [currentVal, ...VINMEC_SPECIALTIES];
  }
  return VINMEC_SPECIALTIES;
};

const formatCurrency = (val?: number | null) => {
  if (val == null || val === 0) return 'Liên hệ tư vấn';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);
};

const normalizePhone = (value: string) => value.replace(/[\s.()-]/g, '');
const phonePattern = /^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$/;
const localToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};
const isMinor = (birthDate: string) => {
  const today = localToday();
  const [year, month, day] = birthDate.split('-').map(Number);
  const [currentYear, currentMonth, currentDay] = today.split('-').map(Number);
  const age = currentYear - year - (currentMonth < month || (currentMonth === month && currentDay < day) ? 1 : 0);
  return age < 18;
};

export const LiveBookingPanel = memo(function LiveBookingPanel({
  intake,
  patientProfileId,
  selectedPatient,
  sessionId,
  isMobileDrawer = false,
  onClose,
  onSubmitted,
}: LiveBookingPanelProps) {
  const accountUser = useSelector((state: RootState) => state.auth.user);
  const authUser = useMemo(() => accountUser && selectedPatient ? { ...accountUser, full_name: selectedPatient.full_name, phone: selectedPatient.contact_phone, date_of_birth: selectedPatient.date_of_birth, gender: selectedPatient.gender } : accountUser, [accountUser, selectedPatient]);

  // Mode: 'doctor' (Khám Chuyên Khoa / Bác Sĩ) vs 'package' (Gói Khám Bệnh / Dịch Vụ)
  const [activeTab, setActiveTab] = useState<'doctor' | 'package'>('doctor');

  // Form State cho Khám Bác Sĩ (Doctor Mode)
  const [patientName, setPatientName] = useState(
    intake?.patient_name || authUser?.full_name || ''
  );
  const [patientPhone, setPatientPhone] = useState(
    intake?.patient_phone || authUser?.phone || ''
  );
  const [dateOfBirth, setDateOfBirth] = useState(
    intake?.date_of_birth || authUser?.date_of_birth || ''
  );
  const [gender, setGender] = useState(
    intake?.gender || authUser?.gender || 'male'
  );
  const [facility, setFacility] = useState(
    intake?.facility_preference || VINMEC_FACILITIES[0]
  );

  const facilityOptions = useMemo(() => {
    if (facility && !VINMEC_FACILITIES.includes(facility)) {
      return [facility, ...VINMEC_FACILITIES];
    }
    return VINMEC_FACILITIES;
  }, [facility]);
  const [preferredDate, setPreferredDate] = useState(intake?.preferred_date || '');
  const [preferredPeriod, setPreferredPeriod] = useState(
    intake?.preferred_period || 'any'
  );
  const [preferredDoctorId, setPreferredDoctorId] = useState(
    intake?.selected_doctor_id || ''
  );
  const [patientNotes, setPatientNotes] = useState(
    intake?.clinical_summary || intake?.patient_notes || ''
  );
  const [guardianName, setGuardianName] = useState('');
  const [guardianPhone, setGuardianPhone] = useState('');
  const [consent, setConsent] = useState(false);
  const editedFields = useRef(new Set<string>());
  const markEdited = (field: string) => editedFields.current.add(field);
  useEffect(() => { editedFields.current.clear(); }, [sessionId]);

  // Ranked specialties for multi-symptom triage
  const [specialties, setSpecialties] = useState<
    Array<{ id: string; name: string; rationale?: string }>
  >(() => {
    if (intake?.ranked_specialties && intake.ranked_specialties.length > 0) {
      return intake.ranked_specialties.map((item, idx) => ({
        id: `spec-${idx}-${item.department_name}`,
        name: item.department_name,
        rationale: item.rationale,
      }));
    }
    if (intake?.specialty_name) {
      return [{ id: 'spec-init-0', name: intake.specialty_name }];
    }
    return [{ id: 'spec-init-0', name: 'Khám Đa khoa & Chuyên khoa' }];
  });

  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const moveSpecialty = (index: number, direction: 'up' | 'down') => {
    markEdited('specialties');
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= specialties.length) return;
    setSpecialties((prev) => {
      const updated = [...prev];
      const temp = updated[index];
      updated[index] = updated[targetIndex];
      updated[targetIndex] = temp;
      return updated;
    });
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    markEdited('specialties');
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    setSpecialties((prev) => {
      const updated = [...prev];
      const [draggedItem] = updated.splice(draggedIndex, 1);
      updated.splice(index, 0, draggedItem);
      return updated;
    });
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleUpdateSpecialty = (index: number, newName: string) => {
    markEdited('specialties');
    setSpecialties((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], name: newName };
      return updated;
    });
  };

  const handleRemoveSpecialty = (index: number) => {
    markEdited('specialties');
    if (specialties.length <= 1) return;
    setSpecialties((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleAddSpecialty = () => {
    markEdited('specialties');
    const existingNames = new Set(specialties.map((s) => s.name));
    const nextSpec = VINMEC_SPECIALTIES.find((s) => !existingNames.has(s)) || 'Khoa Sức khỏe tổng quát';
    setSpecialties((prev) => [
      ...prev,
      {
        id: `spec-${Date.now()}`,
        name: nextSpec,
      },
    ]);
  };

  // State cho Gói Khám Bệnh (Package Mode)
  const [packages, setPackages] = useState<MedicalService[]>([]);
  const [packageFacilities, setPackageFacilities] = useState<Facility[]>([]);
  const [packageFacilityId, setPackageFacilityId] = useState('');
  const [packageCategories, setPackageCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('Tất cả');
  const [packageSearch, setPackageSearch] = useState('');
  const [selectedPackage, setSelectedPackage] = useState<MedicalService | null>(null);
  const [loadingPackages, setLoadingPackages] = useState(false);
  const [packageDate, setPackageDate] = useState('');
  const [packagePeriod, setPackagePeriod] = useState<'morning' | 'afternoon'>('morning');
  const [packageNote, setPackageNote] = useState('');

  // Status & Submission states
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [savedCode, setSavedCode] = useState('');
  const [lastAutoFilledField, setLastAutoFilledField] = useState<string | null>(null);

  // Sync state when intake changes or authUser profile is loaded
  useEffect(() => {
    if (!intake) {
      if (authUser) {
        if (!editedFields.current.has('patientName') && !patientName && authUser.full_name) setPatientName(authUser.full_name);
        if (!editedFields.current.has('patientPhone') && !patientPhone && authUser.phone) setPatientPhone(authUser.phone);
        if (!editedFields.current.has('dateOfBirth') && !dateOfBirth && authUser.date_of_birth) setDateOfBirth(authUser.date_of_birth);
        if (!editedFields.current.has('gender') && authUser.gender) setGender(authUser.gender);
      }
      return;
    }

    // Auto-switch to package mode if agent detects package inquiry
    if (intake.booking_mode === 'package') {
      setActiveTab('package');
    }

    if (!editedFields.current.has('patientName') && intake.patient_name && intake.patient_name !== patientName) {
      setPatientName(intake.patient_name);
      setLastAutoFilledField('name');
    } else if (!editedFields.current.has('patientName') && !patientName && authUser?.full_name) {
      setPatientName(authUser.full_name);
    }

    if (!editedFields.current.has('patientPhone') && intake.patient_phone && intake.patient_phone !== patientPhone) {
      setPatientPhone(intake.patient_phone);
      setLastAutoFilledField('phone');
    } else if (!editedFields.current.has('patientPhone') && !patientPhone && authUser?.phone) {
      setPatientPhone(authUser.phone);
    }

    // Task 1: Auto-sync date_of_birth & gender
    const resolvedDob = intake.date_of_birth || authUser?.date_of_birth;
    if (!editedFields.current.has('dateOfBirth') && resolvedDob && resolvedDob !== dateOfBirth) {
      setDateOfBirth(resolvedDob);
      setLastAutoFilledField('dob');
    }

    const resolvedGender = intake.gender || authUser?.gender;
    if (!editedFields.current.has('gender') && resolvedGender && resolvedGender !== gender) {
      setGender(resolvedGender);
    }

    if (!editedFields.current.has('facility') && intake.facility_preference && intake.facility_preference !== facility) {
      setFacility(intake.facility_preference);
      setLastAutoFilledField('facility');
    }
    if (!editedFields.current.has('preferredDate') && intake.preferred_date && intake.preferred_date !== preferredDate) {
      setPreferredDate(intake.preferred_date);
      setLastAutoFilledField('date');
    }
    if (!editedFields.current.has('preferredPeriod') && intake.preferred_period && intake.preferred_period !== preferredPeriod) {
      setPreferredPeriod(intake.preferred_period);
    }
    if (!editedFields.current.has('preferredDoctorId') && intake.selected_doctor_id && intake.selected_doctor_id !== preferredDoctorId) {
      setPreferredDoctorId(intake.selected_doctor_id);
    }

    // Sync clinical summary notes
    const newSummary = intake.clinical_summary || intake.patient_notes;
    if (!editedFields.current.has('patientNotes') && newSummary && newSummary !== patientNotes) {
      setPatientNotes(newSummary);
      if (!editedFields.current.has('packageNote')) setPackageNote(newSummary);
      setLastAutoFilledField('notes');
    }

    // Sync ranked specialties when intake updates
    if (!editedFields.current.has('specialties') && intake.ranked_specialties && intake.ranked_specialties.length > 0) {
      setSpecialties(
        intake.ranked_specialties.map((item, idx) => ({
          id: `spec-${idx}-${item.department_name}`,
          name: item.department_name,
          rationale: item.rationale,
        }))
      );
    } else if (!editedFields.current.has('specialties') && intake.specialty_name && (!specialties.length || specialties[0].name !== intake.specialty_name)) {
      setSpecialties([
        {
          id: `spec-${Date.now()}`,
          name: intake.specialty_name,
        },
      ]);
    }

    if ((intake as any)?.confirmed && (intake as any)?.request_code && !savedCode) {
      setSavedCode((intake as any).request_code);
    }
  }, [intake, authUser, savedCode]);

  // Load only catalog facilities for package requests.
  useEffect(() => {
    if (activeTab !== 'package') return;
    let active = true;
    void fetchFacilities().then((items) => {
      if (active) setPackageFacilities(items);
    }).catch(() => { if (active) setPackageFacilities([]); });
    return () => { active = false; };
  }, [activeTab]);

  // Load packages catalog when switching to package tab
  useEffect(() => {
    if (activeTab !== 'package') return;
    let active = true;
    if (packageCategories.length === 0) {
      void fetchServiceCategories()
        .then((cats) => {
          if (active) setPackageCategories(cats);
        })
        .catch(() => undefined);
    }

    setLoadingPackages(true);
    const cat = selectedCategory !== 'Tất cả' ? selectedCategory : undefined;
    void fetchServices({ category: cat, name: packageSearch.trim() || undefined, limit: 100 })
      .then((items) => {
        if (active) {
          // Filter out single doctor consultation service to keep health packages
          const pkgs = items.filter((x) => x.code !== 'DV-KHAN-CHUYEN-KHOA');
          setPackages(pkgs);
          if (!selectedPackage && pkgs.length > 0) {
            setSelectedPackage(pkgs[0]);
          }
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoadingPackages(false);
      });

    return () => {
      active = false;
    };
  }, [activeTab, selectedCategory, packageSearch]);

  useEffect(() => {
    if (!packageFacilities.length) return;
    const current = packageFacilities.find((item) => item.id === packageFacilityId);
    if (current) return;
    const matched = packageFacilities.find((item) => item.name === facility);
    setPackageFacilityId((matched || packageFacilities[0]).id);
  }, [packageFacilities, packageFacilityId, facility]);

  const patientError = () => {
    if (patientName.trim().length < 2 || patientName.trim().length > 120) return 'Họ tên người khám cần từ 2 đến 120 ký tự.';
    if (!phonePattern.test(normalizePhone(patientPhone))) return 'Số điện thoại chưa đúng định dạng Việt Nam.';
    const dobErr = birthDateError(dateOfBirth);
    if (dobErr) return dobErr;
    if (isMinor(dateOfBirth) && (guardianName.trim().length < 2 || !phonePattern.test(normalizePhone(guardianPhone)))) {
      return 'Người dưới 18 tuổi cần họ tên và số điện thoại người giám hộ hợp lệ.';
    }
    return '';
  };

  // Calculate completion progress for Doctor Mode
  const requiredFields = [
    Boolean(patientName.trim()),
    Boolean(patientPhone.trim().length >= 9),
    Boolean(dateOfBirth),
    Boolean(facility),
    Boolean(preferredDate),
  ];
  const filledCount = requiredFields.filter(Boolean).length;
  const progressPercent = Math.round((filledCount / requiredFields.length) * 100);

  // Submit Handler for Doctor Mode
  const handleSubmitDoctor = async (e: FormEvent) => {
    e.preventDefault();
    if (!consent) {
      setSubmitError('Vui lòng đồng ý để nhân viên y tế liên hệ xác nhận lịch hẹn.');
      return;
    }
    const error = patientError();
    if (error) { setSubmitError(error); return; }
    if (appointmentDateError(preferredDate)) {
      setSubmitError(appointmentDateError(preferredDate));
      return;
    }

    setSubmitting(true);
    setSubmitError('');

    const primarySpecialty = specialties[0]?.name || intake?.specialty_name || 'Khám Đa khoa & Chuyên khoa';

    // Build combined notes preserving patient summary and ranked specialty sequence
    let finalNotes = patientNotes.trim();
    if (specialties.length > 1) {
      const pipelineText = `\n[Lộ trình ưu tiên người bệnh chọn]: ${specialties.map((s, i) => `${i + 1}. ${s.name}`).join(' -> ')}`;
      if (!finalNotes.includes('[Lộ trình ưu tiên')) {
        finalNotes = finalNotes ? `${finalNotes}\n${pipelineText}` : pipelineText;
      }
    }

    if (finalNotes.length > 1000) {
      setSubmitError('Tóm tắt triệu chứng không được vượt quá 1000 ký tự.');
      setSubmitting(false);
      return;
    }

    const payload = {
      session_id: sessionId,
      patient_profile_id: patientProfileId,
      patient_name: patientName.trim(),
      patient_phone: normalizePhone(patientPhone),
      date_of_birth: dateOfBirth,
      guardian_name: isMinor(dateOfBirth) ? guardianName.trim() : null,
      guardian_phone: isMinor(dateOfBirth) ? normalizePhone(guardianPhone) : null,
      gender: gender || 'other',
      specialty_name: primarySpecialty,
      specialty_code: primarySpecialty === intake?.specialty_name ? intake?.specialty_code || null : null,
      facility_preference: facility,
      preferred_date: preferredDate || null,
      preferred_period: preferredPeriod || 'any',
      preferred_doctor_id: preferredDoctorId || null,
      selected_slot_id: editedFields.current.has('preferredDate') || editedFields.current.has('preferredDoctorId') ? null : intake?.selected_slot_id || null,
      patient_notes: finalNotes || null,
      consent_to_contact: true,
    };

    try {
      const endpoint = intake?.endpoint || '/api/v1/booking-requests';
      const result = await submitBooking(endpoint, payload);
      setSavedCode(result.request_code);
      if (onSubmitted) {
        onSubmitted(result.request_code);
      }
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Không thể lưu thông tin đặt khám. Vui lòng thử lại.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Handler for Package Mode (Task 3)
  const handleSubmitPackage = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedPackage) {
      setSubmitError('Vui lòng chọn một gói khám bệnh hoặc dịch vụ.');
      return;
    }
    if (!consent) { setSubmitError('Vui lòng đồng ý để điều phối viên liên hệ.'); return; }
    const error = patientError();
    if (error) { setSubmitError(error); return; }
    if (appointmentDateError(packageDate)) {
      setSubmitError(appointmentDateError(packageDate));
      return;
    }
    if (!packageFacilityId || !packageFacilities.some((item) => item.id === packageFacilityId)) {
      setSubmitError('Vui lòng chọn cơ sở đang tiếp nhận gói khám.');
      return;
    }
    if (packageNote.trim().length > 1700) { setSubmitError('Ghi chú quá dài.'); return; }

    setSubmitting(true);
    setSubmitError('');

    try {
      const result = await createPackageRequest({
        patient_profile_id: patientProfileId,
        service_id: selectedPackage.id,
        facility_id: packageFacilityId,
        preferred_date: packageDate,
        preferred_period: packagePeriod,
        note: `[Tư vấn qua AI Chatbot] ${packageNote.trim()} | Cơ sở: ${packageFacilities.find((item) => item.id === packageFacilityId)?.name || ''}`,
        patient_name: patientName.trim(),
        patient_phone: normalizePhone(patientPhone),
        date_of_birth: dateOfBirth,
        gender: gender || 'other',
        guardian_name: isMinor(dateOfBirth) ? guardianName.trim() : undefined,
        guardian_phone: isMinor(dateOfBirth) ? normalizePhone(guardianPhone) : undefined,
        consent_to_contact: consent,
      });
      const code = `PKG-${result.id.slice(0, 8).toUpperCase()}`;
      setSavedCode(code);
      if (onSubmitted) {
        onSubmitted(code);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Không thể gửi đăng ký gói khám. Vui lòng thử lại.');
    } finally {
      setSubmitting(false);
    }
  };

  const clinicalDetails = intake?.clinical_details;

  return (
    <div className="flex h-full flex-col bg-slate-50/90 light:bg-app-page/90 dark:bg-[#0c162d]/95 text-slate-900 light:text-app-text dark:text-slate-100">
      {/* ─── PANEL HEADER ─── */}
      <div className="flex items-center justify-between border-b border-slate-200/80 light:border-app-border/80 dark:border-slate-800/80 px-4 py-3 bg-white/80 light:bg-app-surface/80 dark:bg-[#0E1A38]/90 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 light:from-app-primary to-cyan-500 light:to-app-primary text-white shadow-sm shadow-blue-500/30 light:shadow-app-primary/30">
            {activeTab === 'doctor' ? <Calendar className="h-4 w-4" /> : <Package className="h-4 w-4" />}
          </div>
          <div>
            <h4 className="text-xs font-bold leading-tight text-slate-900 light:text-app-text dark:text-white">
              {activeTab === 'doctor' ? 'Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa' : 'Phiếu Đăng Ký Gói Khám Bệnh'}
            </h4>
            <p className="text-[10px] text-slate-500 light:text-app-secondary dark:text-slate-400">
              {authUser ? (
                <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                  <CheckCircle2 className="h-2.5 w-2.5" /> Đồng bộ từ tài khoản
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-blue-600 light:text-app-primary dark:text-cyan-400 font-medium">
                  <Sparkles className="h-2.5 w-2.5" /> AI tự động trích xuất
                </span>
              )}
            </p>
          </div>
        </div>

        {isMobileDrawer && onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 light:text-app-secondary hover:bg-slate-100 light:hover:bg-app-muted dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Đóng phiếu"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ─── TAB SWITCHER: BÁC SĨ vs GÓI KHÁM BỆNH (Task 3) ─── */}
      <div className="grid grid-cols-2 p-1.5 bg-slate-200/70 light:bg-app-tint/70 dark:bg-slate-900/80 border-b border-slate-200 light:border-app-border dark:border-slate-800 text-[11px] font-semibold">
        <button
          type="button"
          onClick={() => {
            setActiveTab('doctor');
            setSubmitError('');
          }}
          className={`flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeTab === 'doctor'
              ? 'bg-white light:bg-app-surface dark:bg-blue-600 text-blue-700 light:text-app-primary dark:text-white shadow-sm font-bold'
              : 'text-slate-600 light:text-app-secondary dark:text-slate-400 hover:text-slate-900 light:hover:text-app-text dark:hover:text-slate-200'
          }`}
        >
          <Stethoscope className="h-3.5 w-3.5" />
          <span>Khám Bác Sĩ</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('package');
            setSubmitError('');
          }}
          className={`relative flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all cursor-pointer ${
            activeTab === 'package'
              ? 'bg-white light:bg-app-surface dark:bg-blue-600 text-blue-700 light:text-app-primary dark:text-white shadow-sm font-bold'
              : 'text-slate-600 light:text-app-secondary dark:text-slate-400 hover:text-slate-900 light:hover:text-app-text dark:hover:text-slate-200'
          }`}
        >
          <Package className="h-3.5 w-3.5" />
          <span>Gói Khám Bệnh</span>
          {intake?.booking_mode === 'package' && (
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 light:bg-app-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500 light:bg-app-primary" />
            </span>
          )}
        </button>
      </div>

      {/* Progress & Status Indicators */}
      {activeTab === 'doctor' && (
        <div className="border-b border-slate-200/60 light:border-app-border/60 dark:border-slate-800/60 bg-blue-50/50 light:bg-app-muted/50 dark:bg-blue-950/20 px-4 py-2 text-[11px]">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="font-semibold text-slate-700 light:text-app-text dark:text-slate-300">
              Tiến độ: {filledCount}/5 thông tin
            </span>
            <span className="font-bold text-blue-600 light:text-app-primary dark:text-cyan-400 font-mono">
              {progressPercent}%
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 light:bg-app-tint dark:bg-slate-800">
            <div
              className="h-full bg-gradient-to-r from-blue-600 light:from-app-primary to-cyan-500 light:to-app-primary transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {intake?.specialty_name && (
            <div className="mt-2 flex items-center gap-1.5 text-[10.5px] font-medium text-blue-800 light:text-app-primary-strong dark:text-cyan-300">
              <Stethoscope className="h-3 w-3 shrink-0 text-blue-600 light:text-app-primary dark:text-cyan-400" />
              <span className="truncate">
                Chuyên khoa: <strong>{intake.specialty_name}</strong>
              </span>
            </div>
          )}
        </div>
      )}

      {/* ─── BODY CONTENT ─── */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5 text-xs">
        {/* SUCCESS NOTIFICATION */}
        {savedCode ? (
          <div className="flex flex-col items-center justify-center py-6 text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-700 shadow-sm animate-bounce">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h5 className="text-sm font-bold text-slate-900 light:text-app-text dark:text-white">
              Đã gửi yêu cầu đăng ký khám thành công!
            </h5>
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-[#071d18] px-3.5 py-2 text-xs">
              <p className="text-slate-500 light:text-app-secondary dark:text-slate-400 text-[10.5px]">Mã phiếu tiếp nhận:</p>
              <p className="text-base font-extrabold font-mono text-emerald-700 dark:text-emerald-300">
                {savedCode}
              </p>
            </div>
            <p className="text-[11.5px] text-slate-600 light:text-app-secondary dark:text-slate-300 leading-relaxed max-w-xs">
              Điều phối viên y tế Vinmec sẽ liên hệ qua số điện thoại <strong>{patientPhone}</strong> để hỗ trợ xếp lịch và tư vấn chuẩn bị trước khi đến khám.
            </p>
            <button
              type="button"
              onClick={() => setSavedCode('')}
              className="mt-2 text-[11px] font-semibold text-blue-600 light:text-app-primary dark:text-cyan-400 hover:underline cursor-pointer"
            >
              Tạo phiếu hẹn mới
            </button>
          </div>
        ) : activeTab === 'doctor' ? (
          /* ─── MODE 1: FORM KHÁM BÁC SĨ (ĐỒNG BỘ VỚI CONSULTATION BOOKING) ─── */
          <form onSubmit={handleSubmitDoctor} className="space-y-3">
            {submitError && (
              <div className="flex items-start gap-1.5 rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 p-2.5 text-[11px] text-red-700 dark:text-red-300">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{submitError}</span>
              </div>
            )}

            {/* BƯỚC 1: THÔNG TIN NGƯỜI KHÁM (Task 1: Auto DOB & Gender) */}
            <div className="rounded-xl border border-slate-200/80 light:border-app-border/80 dark:border-slate-800 bg-white/60 light:bg-app-surface/60 dark:bg-slate-900/60 p-3 space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-100 light:border-app-border dark:border-slate-800 pb-1.5">
                <span className="font-bold text-[11px] text-slate-800 light:text-app-text dark:text-slate-200 flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-blue-600 light:text-app-primary dark:text-cyan-400" />
                  1. Thông tin người khám
                </span>
                {authUser && (
                  <span className="text-[9.5px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                    Đã xác thực
                  </span>
                )}
              </div>

              {/* Patient Name */}
              <div>
                <label className="flex items-center justify-between text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                  <span>Họ và tên bệnh nhân *</span>
                  {lastAutoFilledField === 'name' && (
                    <span className="text-[9px] text-cyan-600 light:text-app-primary dark:text-cyan-400">Tự động điền</span>
                  )}
                </label>
                <input
                  type="text"
                  value={patientName}
                  maxLength={120}
                  onChange={(e) => { markEdited('patientName'); setPatientName(e.target.value); }}
                  placeholder="Ví dụ: Nguyễn Văn An"
                  required
                  className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2.5 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                />
              </div>

              {/* Patient Phone */}
              <div>
                <label className="flex items-center justify-between text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                  <span>Số điện thoại liên hệ *</span>
                  {lastAutoFilledField === 'phone' && (
                    <span className="text-[9px] text-cyan-600 light:text-app-primary dark:text-cyan-400">Tự động điền</span>
                  )}
                </label>
                <input
                  type="tel"
                  value={patientPhone}
                  maxLength={20}
                  onChange={(e) => { markEdited('patientPhone'); setPatientPhone(e.target.value); }}
                  placeholder="Ví dụ: 0912345678"
                  required
                  className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2.5 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                />
              </div>

              {/* Date of Birth & Gender (Task 1) */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                    Ngày sinh (dd/mm/yyyy) *
                  </label>
                  <DateInputVN
                    value={dateOfBirth}
                    max={localToday()}
                    onChange={(e) => { markEdited('dateOfBirth'); setDateOfBirth(e.target.value); }}
                    required
                    placeholder="dd/mm/yyyy"
                    className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                  />
                </div>

                <div>
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                    Giới tính *
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => { markEdited('gender'); setGender(e.target.value); }}
                    className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                  >
                    <option value="male">Nam</option>
                    <option value="female">Nữ</option>
                    <option value="other">Khác</option>
                  </select>
                </div>
              </div>
            </div>

            {/* BƯỚC 2: CƠ SỞ & LỊCH KHÁM */}
            <div className="rounded-xl border border-slate-200/80 light:border-app-border/80 dark:border-slate-800 bg-white/60 light:bg-app-surface/60 dark:bg-slate-900/60 p-3 space-y-2.5">
              <span className="font-bold text-[11px] text-slate-800 light:text-app-text dark:text-slate-200 flex items-center gap-1.5 border-b border-slate-100 light:border-app-border dark:border-slate-800 pb-1.5">
                <Hospital className="h-3.5 w-3.5 text-blue-600 light:text-app-primary dark:text-cyan-400" />
                2. Cơ sở & Thời gian mong muốn
              </span>

              {/* Specialty Section with Ranked Multi-Specialty Pipeline */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300">
                    Chuyên khoa thăm khám
                  </label>
                  <div className="flex items-center gap-1.5">
                    {specialties.length > 1 ? (
                      <span className="inline-flex items-center gap-1 text-[9.5px] font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/70 border border-blue-200/60 dark:border-blue-800/60 px-1.5 py-0.5 rounded-full">
                        <Sparkles className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                        Lộ trình ({specialties.length} khoa)
                      </span>
                    ) : (
                      <span className="text-[9.5px] text-emerald-700 dark:text-emerald-300 bg-emerald-100/70 dark:bg-emerald-950/60 px-1.5 py-0.5 rounded font-normal shrink-0">
                        AI Định hướng
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={handleAddSpecialty}
                      className="inline-flex items-center gap-1 text-[9.5px] font-medium text-emerald-700 dark:text-emerald-400 hover:text-emerald-800 bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200/70 dark:border-emerald-800 px-1.5 py-0.5 rounded transition-colors"
                      title="Thêm chuyên khoa cần phối hợp khám"
                    >
                      <Plus className="h-3 w-3" />
                      Thêm khoa
                    </button>
                  </div>
                </div>

                {/* Ranked Draggable List Cards */}
                <div className="space-y-1.5">
                  {specialties.map((item, index) => {
                    const isFirst = index === 0;
                    const isLast = index === specialties.length - 1;
                    return (
                      <div
                        key={item.id}
                        draggable
                        onDragStart={() => handleDragStart(index)}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragEnd={handleDragEnd}
                        className={`group relative flex items-center gap-1.5 p-2 rounded-lg border transition-all ${
                          draggedIndex === index
                            ? 'opacity-40 border-dashed border-blue-400 bg-blue-50/50 dark:bg-blue-950/20'
                            : isFirst
                            ? 'border-emerald-200/90 dark:border-emerald-800/80 bg-gradient-to-r from-emerald-50/60 to-white dark:from-emerald-950/30 dark:to-slate-900 shadow-2xs'
                            : 'border-slate-200 light:border-app-border dark:border-slate-800 bg-white/90 light:bg-app-surface/90 dark:bg-slate-900/90 hover:border-slate-300 dark:hover:border-slate-700'
                        }`}
                      >
                        {/* Drag Handle */}
                        <div
                          className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-0.5 rounded touch-none shrink-0"
                          title="Kéo thả để đổi thứ tự ưu tiên khám"
                        >
                          <GripVertical className="h-3.5 w-3.5" />
                        </div>

                        {/* Priority Badge */}
                        <div className="shrink-0 flex items-center">
                          <span
                            className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-bold ${
                              isFirst
                                ? 'bg-emerald-600 text-white shadow-2xs'
                                : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                            }`}
                          >
                            {index + 1}
                          </span>
                        </div>

                        {/* Specialty Selector Dropdown */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1">
                            <select
                              value={item.name}
                              onChange={(e) => handleUpdateSpecialty(index, e.target.value)}
                              className="w-full bg-transparent font-medium text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none cursor-pointer focus:ring-1 focus:ring-emerald-500 rounded py-0.5 pr-1 truncate"
                            >
                              {getSpecialtyOptions(item.name).map((opt) => (
                                <option
                                  key={opt}
                                  value={opt}
                                  className="text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900"
                                >
                                  {opt}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span
                              className={`text-[9px] font-medium ${
                                isFirst
                                  ? 'text-emerald-700 dark:text-emerald-400'
                                  : 'text-slate-500 dark:text-slate-400'
                              }`}
                            >
                              {isFirst ? 'Ưu tiên 1 (Khám trước)' : `Khám phối hợp bước ${index + 1}`}
                            </span>
                            {item.rationale && (
                              <span className="text-[9px] text-slate-400 dark:text-slate-500 truncate" title={item.rationale}>
                                • {item.rationale}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Action Controls: Up, Down, Delete */}
                        <div className="flex items-center gap-0.5 shrink-0 opacity-80 group-hover:opacity-100">
                          <button
                            type="button"
                            onClick={() => moveSpecialty(index, 'up')}
                            disabled={isFirst}
                            className={`p-1 rounded text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                              isFirst ? 'opacity-20 cursor-not-allowed' : ''
                            }`}
                            title="Di chuyển lên trên"
                          >
                            <ArrowUp className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            onClick={() => moveSpecialty(index, 'down')}
                            disabled={isLast}
                            className={`p-1 rounded text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
                              isLast ? 'opacity-20 cursor-not-allowed' : ''
                            }`}
                            title="Di chuyển xuống dưới"
                          >
                            <ArrowDown className="h-3 w-3" />
                          </button>
                          {specialties.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleRemoveSpecialty(index)}
                              className="p-1 rounded text-rose-500 hover:text-rose-700 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                              title="Xóa chuyên khoa này"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Micro-hint for UX */}
                <p className="text-[9.5px] text-slate-500 dark:text-slate-400 leading-tight flex items-center gap-1 pt-0.5">
                  <Info className="h-3 w-3 text-slate-400 shrink-0" />
                  Kéo thả hoặc bấm mũi tên để đổi thứ tự ưu tiên khám; bấm vào tên khoa để thay đổi.
                </p>
              </div>

              {/* Facility */}
              <div>
                <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                  Cơ sở Vinmec tiếp nhận
                </label>
                <select
                  value={facility}
                  onChange={(e) => { markEdited('facility'); setFacility(e.target.value); }}
                  className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2.5 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                >
                  {facilityOptions.map((fac) => (
                    <option key={fac} value={fac}>
                      {fac}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date & Period */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                    Ngày khám (dd/mm/yyyy) *
                  </label>
                  <DateInputVN
                    value={preferredDate}
                    min={localToday()}
                    max={latestAppointmentDate()}
                    onChange={(e) => { markEdited('preferredDate'); setPreferredDate(e.target.value); }}
                    required
                    placeholder="dd/mm/yyyy"
                    className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                  />
                </div>

                <div>
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                    Buổi khám
                  </label>
                  <select
                    value={preferredPeriod}
                    onChange={(e) => { markEdited('preferredPeriod'); setPreferredPeriod(e.target.value); }}
                    className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs"
                  >
                    <option value="any">Cả ngày / Bất kỳ</option>
                    <option value="morning">Buổi sáng</option>
                    <option value="afternoon">Buổi chiều</option>
                  </select>
                </div>
              </div>

              {/* Preferred Doctor Dropdown (luôn hiển thị để bệnh nhân chọn bác sĩ hoặc để điều phối viên sắp xếp) */}
              <div>
                <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                  Bác sĩ chuyên khoa tiếp nhận
                </label>
                <select
                  value={preferredDoctorId}
                  onChange={(e) => { markEdited('preferredDoctorId'); setPreferredDoctorId(e.target.value); }}
                  className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700/80 bg-white light:bg-app-surface dark:bg-slate-900 px-2.5 py-1.5 text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary text-xs truncate"
                >
                  <option value="">Để Điều phối viên chỉ định Bác sĩ phù hợp nhất</option>
                  {intake?.doctors && intake.doctors.length > 0 && intake.doctors.map((doc) => (
                    <option key={doc.id || doc.name} value={doc.id || doc.name}>
                      {doc.name} {doc.title ? `— ${doc.title}` : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* BƯỚC 3: LÝ DO KHÁM & TÓM TẮT LÂM SÀNG TỪ AGENT (Task 2) */}
            <div className="rounded-xl border border-blue-200/80 light:border-app-border/80 dark:border-blue-900/60 bg-blue-50/40 light:bg-app-muted/40 dark:bg-blue-950/20 p-3 space-y-2">
              <div className="flex items-center justify-between border-b border-blue-200/50 light:border-app-border/50 dark:border-blue-900/40 pb-1.5">
                <span className="font-bold text-[11px] text-blue-900 light:text-app-primary-strong dark:text-cyan-300 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-blue-600 light:text-app-primary dark:text-cyan-400" />
                  3. Lý do khám & Tóm tắt triệu chứng
                </span>
                <span className="text-[9.5px] font-medium text-blue-700 light:text-app-primary dark:text-cyan-300 bg-blue-100/70 light:bg-app-tint/70 dark:bg-blue-900/50 px-1.5 py-0.5 rounded">
                  AI Thu thập chuẩn
                </span>
              </div>

              {/* Clinical Details Chips (Vị trí, Mức độ, Thời gian, Kèm theo) */}
              {clinicalDetails && (
                <div className="flex flex-wrap gap-1 py-1">
                  {clinicalDetails.location && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-0.5 text-[10px] font-medium text-slate-700 light:text-app-text dark:text-slate-300 border border-slate-200 light:border-app-border dark:border-slate-800 shadow-2xs">
                      📍 Vị trí: <strong>{clinicalDetails.location}</strong>
                    </span>
                  )}
                  {clinicalDetails.severity && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 dark:bg-amber-950/50 px-2 py-0.5 text-[10px] font-medium text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-900 shadow-2xs">
                      ⚡ Mức độ: <strong>{clinicalDetails.severity}</strong>
                    </span>
                  )}
                  {clinicalDetails.duration && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-0.5 text-[10px] font-medium text-slate-700 light:text-app-text dark:text-slate-300 border border-slate-200 light:border-app-border dark:border-slate-800 shadow-2xs">
                      ⏱️ <strong>{clinicalDetails.duration}</strong>
                    </span>
                  )}
                  {clinicalDetails.associated && clinicalDetails.associated.length > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 light:bg-app-muted dark:bg-blue-950/50 px-2 py-0.5 text-[10px] font-medium text-blue-800 light:text-app-primary-strong dark:text-cyan-300 border border-blue-200 light:border-app-border dark:border-blue-900 shadow-2xs">
                      🩺 Kèm: {clinicalDetails.associated.join(', ')}
                    </span>
                  )}
                  {clinicalDetails.negatives && clinicalDetails.negatives.length > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 text-[10px] font-medium text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900 shadow-2xs">
                      🛡️ {clinicalDetails.negatives.join(', ')}
                    </span>
                  )}
                </div>
              )}

              {/* Textarea lý do khám / tóm tắt triệu chứng */}
              <textarea
                value={patientNotes}
                onChange={(e) => { markEdited('patientNotes'); setPatientNotes(e.target.value); }}
                placeholder="Agent đang tổng hợp tóm tắt triệu chứng từ hội thoại..."
                rows={3}
                className="w-full rounded-lg border border-blue-200 light:border-app-border dark:border-blue-800/80 bg-white light:bg-app-surface dark:bg-slate-900 p-2 text-slate-900 light:text-app-text dark:text-slate-100 placeholder:text-slate-400 light:placeholder:text-app-secondary outline-none focus:border-blue-500 light:focus:border-app-primary text-xs resize-none leading-relaxed"
              />
              <p className="text-[10px] text-slate-500 light:text-app-secondary dark:text-slate-400 italic">
                * Bác có thể trực tiếp bổ sung hoặc chỉnh sửa lại tóm tắt triệu chứng ở trên.
              </p>
            </div>

              {dateOfBirth && isMinor(dateOfBirth) && (
                <div className="grid grid-cols-2 gap-2 rounded-lg border border-amber-200 p-2">
                  <label className="text-xs">Họ tên người giám hộ *
                    <input type="text" value={guardianName} onChange={(e) => { markEdited('guardianName'); setGuardianName(e.target.value); }} maxLength={120} required className="mt-1 w-full rounded border p-1.5 text-slate-900" />
                  </label>
                  <label className="text-xs">Số điện thoại người giám hộ *
                    <input type="tel" value={guardianPhone} onChange={(e) => { markEdited('guardianPhone'); setGuardianPhone(e.target.value); }} maxLength={20} required className="mt-1 w-full rounded border p-1.5 text-slate-900" />
                  </label>
                </div>
              )}

            {/* Consent & Submit Button */}
            <label className="flex items-start gap-2 pt-0.5 text-[10.5px] leading-relaxed text-slate-600 light:text-app-secondary dark:text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 rounded text-blue-600 light:text-app-primary focus:ring-blue-500 light:focus:ring-app-primary"
              />
              <span>
                Tôi xác nhận thông tin trên và đồng ý để Điều phối viên y tế liên hệ xếp lịch.
              </span>
            </label>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-gradient-to-r from-blue-600 light:from-app-primary to-cyan-600 light:to-app-primary hover:from-blue-500 light:hover:from-app-primary hover:to-cyan-500 light:hover:to-app-primary text-white font-semibold py-2.5 shadow-md shadow-blue-500/25 light:shadow-app-primary/25 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <TypewriterLoader />
                  <span>Đang gửi thông tin…</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-4 w-4" />
                  <span>Xác nhận gửi thông tin đặt khám</span>
                </>
              )}
            </button>
          </form>
        ) : (
          /* ─── MODE 2: ĐĂNG KÝ GÓI KHÁM BỆNH / DỊCH VỤ (Task 3) ─── */
          <form onSubmit={handleSubmitPackage} className="space-y-3">
            {submitError && (
              <div className="flex items-start gap-1.5 rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 p-2.5 text-[11px] text-red-700 dark:text-red-300">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{submitError}</span>
              </div>
            )}

            {/* Search & Category Filter */}
            <div className="space-y-1.5">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400 light:text-app-secondary" />
                <input
                  type="text"
                  placeholder="Tìm kiếm gói khám, tầm soát…"
                  value={packageSearch}
                  onChange={(e) => setPackageSearch(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                />
              </div>

              {/* Category Pills */}
              <div className="flex items-center gap-1 overflow-x-auto pb-1 no-scrollbar text-[10.5px]">
                <button
                  type="button"
                  onClick={() => setSelectedCategory('Tất cả')}
                  className={`shrink-0 px-2 py-0.5 rounded-full font-medium cursor-pointer transition-colors ${
                    selectedCategory === 'Tất cả'
                      ? 'bg-blue-600 light:bg-app-primary text-white'
                      : 'bg-slate-200/80 light:bg-app-tint/80 dark:bg-slate-800 text-slate-700 light:text-app-text dark:text-slate-300 hover:bg-slate-300'
                  }`}
                >
                  Tất cả
                </button>
                {packageCategories.slice(0, 8).map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`shrink-0 px-2 py-0.5 rounded-full font-medium cursor-pointer transition-colors ${
                      selectedCategory === cat
                        ? 'bg-blue-600 light:bg-app-primary text-white'
                        : 'bg-slate-200/80 light:bg-app-tint/80 dark:bg-slate-800 text-slate-700 light:text-app-text dark:text-slate-300 hover:bg-slate-300'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* List of Available Packages */}
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {loadingPackages ? (
                <div className="py-6 text-center text-slate-400 light:text-app-secondary text-xs flex items-center justify-center gap-2">
                  <TypewriterLoader />
                  <span>Đang tải danh sách gói khám…</span>
                </div>
              ) : packages.length === 0 ? (
                <p className="py-4 text-center text-slate-400 light:text-app-secondary text-xs">
                  Không tìm thấy gói khám phù hợp với từ khóa này.
                </p>
              ) : (
                packages.map((pkg) => {
                  const isSelected = selectedPackage?.id === pkg.id;
                  return (
                    <div
                      key={pkg.id}
                      onClick={() => setSelectedPackage(pkg)}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'border-blue-600 light:border-app-primary dark:border-cyan-500 bg-blue-50/80 light:bg-app-muted/80 dark:bg-blue-950/40 ring-1 ring-blue-500/20 light:ring-app-primary/20 shadow-xs'
                          : 'border-slate-200 light:border-app-border dark:border-slate-800 bg-white light:bg-app-surface dark:bg-slate-900 hover:border-blue-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-1.5">
                        <span className="font-bold text-[11.5px] text-slate-900 light:text-app-text dark:text-slate-100 leading-snug">
                          {pkg.name}
                        </span>
                        {isSelected && (
                          <span className="shrink-0 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 light:bg-app-primary text-white text-[10px]">
                            <Check className="h-2.5 w-2.5" />
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[10.5px]">
                        <span className="text-slate-500 light:text-app-secondary dark:text-slate-400">
                          {pkg.category || 'Gói chăm sóc sức khỏe'}
                        </span>
                        <span className="font-bold text-blue-600 light:text-app-primary dark:text-cyan-400">
                          {formatCurrency(pkg.price)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Selected Package Details & Schedule */}
            {selectedPackage && (
              <div className="rounded-xl border border-blue-200 light:border-app-border dark:border-blue-900/60 bg-blue-50/30 light:bg-app-muted/30 dark:bg-blue-950/20 p-3 space-y-2.5">
                <div className="border-b border-blue-200/50 light:border-app-border/50 pb-1.5">
                  <p className="text-[10px] text-blue-700 light:text-app-primary dark:text-cyan-300 font-semibold uppercase">
                    Gói dịch vụ đã chọn:
                  </p>
                  <p className="text-xs font-bold text-slate-900 light:text-app-text dark:text-white">
                    {selectedPackage.name}
                  </p>
                  <p className="text-[11px] font-bold text-blue-600 light:text-app-primary dark:text-cyan-400 mt-0.5">
                    Giá niêm yết: {formatCurrency(selectedPackage.price)}
                  </p>
                </div>

                {/* Facility */}
                <div>
                  <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                    Cơ sở Vinmec thực hiện
                  </label>
                  <select
                    value={packageFacilityId}
                    onChange={(e) => { setPackageFacilityId(e.target.value); setFacility(packageFacilities.find((item) => item.id === e.target.value)?.name || ''); markEdited('facility'); }}
                    className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                  >
                    {packageFacilities.map((fac) => (
                      <option key={fac.id} value={fac.id}>
                        {fac.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Preferred Date & Period */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                      Ngày khám (dd/mm/yyyy) *
                    </label>
                    <DateInputVN
                      value={packageDate}
                      min={localToday()}
                      max={latestAppointmentDate()}
                      onChange={(e) => setPackageDate(e.target.value)}
                      required
                      placeholder="dd/mm/yyyy"
                      className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                    />
                  </div>

                  <div>
                    <label className="block text-[10.5px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                      Buổi khám
                    </label>
                    <select
                      value={packagePeriod}
                      onChange={(e) => setPackagePeriod(e.target.value as 'morning' | 'afternoon')}
                      className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                    >
                      <option value="morning">Buổi sáng</option>
                      <option value="afternoon">Buổi chiều</option>
                    </select>
                  </div>
                </div>

                {/* Patient Information (Task 1: Auto DOB & Gender) */}
                <div className="space-y-2 border-t border-blue-200/50 light:border-app-border/50 dark:border-blue-900/40 pt-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                        Họ tên người khám *
                      </label>
                      <input
                        type="text"
                        value={patientName}
                        maxLength={120}
                        onChange={(e) => { markEdited('patientName'); setPatientName(e.target.value); }}
                        placeholder="Họ và tên"
                        required
                        className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                        Số điện thoại *
                      </label>
                      <input
                        type="tel"
                        value={patientPhone}
                        maxLength={20}
                        onChange={(e) => { markEdited('patientPhone'); setPatientPhone(e.target.value); }}
                        placeholder="Số ĐT"
                        required
                        className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                        Ngày sinh (dd/mm/yyyy) *
                      </label>
                      <DateInputVN
                        value={dateOfBirth}
                        max={localToday()}
                        onChange={(e) => { markEdited('dateOfBirth'); setDateOfBirth(e.target.value); }}
                        required
                        placeholder="dd/mm/yyyy"
                        className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                        Giới tính
                      </label>
                      <select
                        value={gender}
                        onChange={(e) => { markEdited('gender'); setGender(e.target.value); }}
                        className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary"
                      >
                        <option value="male">Nam</option>
                        <option value="female">Nữ</option>
                        <option value="other">Khác</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-semibold text-slate-700 light:text-app-text dark:text-slate-300 mb-0.5">
                      Ghi chú / Nhu cầu đặc biệt
                    </label>
                    <textarea
                      value={packageNote}
                      onChange={(e) => { markEdited('packageNote'); setPackageNote(e.target.value); }}
                      placeholder="Ghi chú thêm về tiền sử bệnh lý hoặc nhu cầu riêng…"
                      rows={2}
                      className="w-full rounded-lg border border-slate-200 light:border-app-border dark:border-slate-700 bg-white light:bg-app-surface dark:bg-slate-900 p-2 text-xs text-slate-900 light:text-app-text dark:text-slate-100 outline-none focus:border-blue-500 light:focus:border-app-primary resize-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {dateOfBirth && isMinor(dateOfBirth) && (
              <div className="grid grid-cols-2 gap-2 rounded-lg border border-amber-200 p-2">
                <label className="text-xs">Họ tên người giám hộ *
                  <input type="text" value={guardianName} onChange={(e) => { markEdited('guardianName'); setGuardianName(e.target.value); }} maxLength={120} required className="mt-1 w-full rounded border p-1.5 text-slate-900" />
                </label>
                <label className="text-xs">Số điện thoại người giám hộ *
                  <input type="tel" value={guardianPhone} onChange={(e) => { markEdited('guardianPhone'); setGuardianPhone(e.target.value); }} maxLength={20} required className="mt-1 w-full rounded border p-1.5 text-slate-900" />
                </label>
              </div>
            )}
            <label className="flex items-start gap-2 text-xs text-slate-600">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
              Tôi xác nhận thông tin và đồng ý để Điều phối viên y tế liên hệ.
            </label>
            <button
              type="submit"
              disabled={submitting || !selectedPackage}
              className="w-full rounded-xl bg-gradient-to-r from-blue-600 light:from-app-primary to-cyan-600 light:to-app-primary hover:from-blue-500 light:hover:from-app-primary hover:to-cyan-500 light:hover:to-app-primary text-white font-semibold py-2.5 shadow-md shadow-blue-500/25 light:shadow-app-primary/25 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <TypewriterLoader />
                  <span>Đang gửi đăng ký gói khám…</span>
                </>
              ) : (
                <>
                  <Package className="h-4 w-4" />
                  <span>Gửi yêu cầu đăng ký Gói Khám</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
});
