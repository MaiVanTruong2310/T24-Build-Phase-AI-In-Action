import { TypewriterLoader } from '../components/TypewriterLoader';
import {
  ArrowLeft,
  CalendarClock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  QrCode,
  RefreshCw,
  Stethoscope,
  UserRoundCheck,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchWithAuth } from '../app/apiClient';
import {
  Booking,
  BookingStatus,
  cancelBooking,
  fetchBooking,
  fetchDoctors,
  fetchFacilities,
  fetchMyPackageRequests,
  fetchServices,
  fetchSpecialties,
  PackageRequest,
  reschedulePackageRequest,
} from '../features/appointment-booking/api';
import { DateInputVN } from '../components/DateInputVN';
import { HITLProgress } from '../features/appointment-progress/components/HITLProgress';
import {
  BookingListItem,
  formatDateOnlyVN,
  getDisplayData,
  LiveCoordinationCase,
  toCatalogMap,
} from '../features/appointment-progress/utils';
import { AppointmentCatalog } from '../features/appointment-progress/types';

function statusStyle(status: Booking['status']): string {
  if (status === 'pending_approval') {
    return 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300';
  }
  if (status === 'confirmed') {
    return 'border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/50 text-teal-800 dark:text-teal-300';
  }
  if (status === 'rejected') {
    return 'border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300';
  }
  return 'border-slate-200 dark:border-app-border bg-slate-100 dark:bg-app-muted text-slate-600 dark:text-app-secondary';
}

function statusLabel(status: Booking['status'], type: 'doctor_visit' | 'package' | 'coordination'): string {
  if (status === 'pending_approval') {
    if (type === 'package') return 'Chờ điều phối tư vấn gói';
    if (type === 'coordination') return 'Đang xử lý phân luồng';
    return 'Chờ xác nhận';
  }
  if (status === 'confirmed') return 'Đã xác nhận';
  if (status === 'rejected') return 'Đã từ chối';
  if (status === 'expired') return 'Đã hết hạn';
  return 'Đã hủy';
}

export default function AppointmentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [bookingItem, setBookingItem] = useState<BookingListItem | null>(null);
  const [catalog, setCatalog] = useState<AppointmentCatalog>({
    doctors: new Map(),
    facilities: new Map(),
    services: new Map(),
    specialties: new Map(),
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [showRescheduleDialog, setShowRescheduleDialog] = useState(false);
  const [newPackageDate, setNewPackageDate] = useState('');
  const [newPackagePeriod, setNewPackagePeriod] = useState<'morning' | 'afternoon'>('morning');
  const [newPackageFacilityId, setNewPackageFacilityId] = useState('');
  const [rescheduleNote, setRescheduleNote] = useState('');
  const [isRescheduling, setIsRescheduling] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (!id) {
      setError('Mã lịch hẹn không hợp lệ.');
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError('');

    const loadAll = async () => {
      try {
        const [
          bookingRes,
          packageRequestsRes,
          liveCasesRes,
          doctorsRes,
          facilitiesRes,
          servicesRes,
          specialtiesRes,
        ] = await Promise.allSettled([
          fetchBooking(id),
          fetchMyPackageRequests().catch(() => [] as PackageRequest[]),
          fetchWithAuth('/coordination/live/mine').then(async (res) => {
            if (!res.ok) return [];
            const json = await res.json();
            return Array.isArray(json.data) ? (json.data as LiveCoordinationCase[]) : [];
          }),
          fetchDoctors(),
          fetchFacilities(),
          fetchServices(),
          fetchSpecialties(),
        ]);

        if (!isMounted) return;

        const currentCatalog: AppointmentCatalog = {
          doctors: doctorsRes.status === 'fulfilled' ? toCatalogMap(doctorsRes.value) : new Map(),
          facilities: facilitiesRes.status === 'fulfilled' ? toCatalogMap(facilitiesRes.value) : new Map(),
          services: servicesRes.status === 'fulfilled' ? toCatalogMap(servicesRes.value) : new Map(),
          specialties: specialtiesRes.status === 'fulfilled' ? toCatalogMap(specialtiesRes.value) : new Map(),
        };
        setCatalog(currentCatalog);

        // 1. Kiểm tra nếu là Direct Booking
        if (bookingRes.status === 'fulfilled' && bookingRes.value) {
          const direct = bookingRes.value as BookingListItem;
          const svc = currentCatalog.services.get(direct.service_id);
          const isGroup = direct.booking_mode === 'group' || svc?.booking_mode === 'group';
          setBookingItem({
            ...direct,
            booking_mode: isGroup ? 'package' : (direct.booking_mode || 'doctor_visit'),
          });
          setIsLoading(false);
          return;
        }

        // 2. Kiểm tra nếu là Package Request
        const packages: PackageRequest[] = packageRequestsRes.status === 'fulfilled' ? packageRequestsRes.value : [];
        let foundPkg = packages.find((p) => p.id === id);

        // 3. Kiểm tra nếu là Coordination Case
        const liveCases: LiveCoordinationCase[] = liveCasesRes.status === 'fulfilled' ? liveCasesRes.value : [];
        const foundCase = liveCases.find((c) => c.id === id);

        // Nếu id tương ứng với một case của package, ưu tiên hiển thị gói khám
        if (!foundPkg && foundCase) {
          const srcId = (foundCase as { source_id?: string }).source_id;
          if ((foundCase as { source?: string }).source === 'package' || srcId) {
            foundPkg = packages.find((p) => p.id === srcId || p.id === id);
          }
        }

        if (foundPkg) {
          const timeStr = foundPkg.preferred_period === 'afternoon' ? 'T13:30:00+07:00' : 'T08:00:00+07:00';
          const startsAt = foundPkg.preferred_date
            ? foundPkg.preferred_date.includes('T')
              ? foundPkg.preferred_date
              : `${foundPkg.preferred_date}${timeStr}`
            : foundPkg.created_at || new Date().toISOString();
          const statusMap: Record<string, BookingStatus> = {
            pending: 'pending_approval',
            contacted: 'pending_approval',
            confirmed: 'confirmed',
            completed: 'confirmed',
            cancelled: 'cancelled',
          };
          const item: BookingListItem = {
            id: foundPkg.id,
            user_id: foundPkg.patient_id || '',
            schedule_id: null,
            hold_id: null,
            doctor_id: '',
            facility_id: foundPkg.facility_id,
            starts_at: startsAt,
            ends_at: startsAt,
            booking_mode: 'package',
            service_id: foundPkg.service_id,
            specialty_id: '',
            encounter_type: 'in_person',
            reason: foundPkg.note || `Đăng ký ${foundPkg.service_name || 'Gói khám sức khỏe'}`,
            patient_note: foundPkg.staff_note || null,
            status: statusMap[foundPkg.status] || 'pending_approval',
            cancellation_reason: null,
            created_at: foundPkg.created_at || startsAt,
            updated_at: foundPkg.created_at || startsAt,
            packageRequest: foundPkg,
            coordinationCase: foundCase,
          };
          setBookingItem(item);
          setIsLoading(false);
          return;
        }

        if (foundCase) {
          const prefDate = foundCase.patient?.preferred_date;
          const prefPeriod = foundCase.patient?.preferred_period;
          const timeStr = prefPeriod === 'afternoon' ? 'T13:30:00+07:00' : 'T08:30:00+07:00';
          const startsAt = prefDate
            ? prefDate.includes('T')
              ? prefDate
              : `${prefDate}${timeStr}`
            : foundCase.created_at;
          const statusMap: Record<string, BookingStatus> = {
            new: 'pending_approval',
            contacting: 'pending_approval',
            waiting_patient: 'pending_approval',
            waiting_deposit: 'pending_approval',
            deposit_verified: 'pending_approval',
            confirmed: 'confirmed',
            completed: 'confirmed',
            cancelled: 'cancelled',
          };
          const symptoms = foundCase.ai_snapshot?.symptoms;
          const reason =
            foundCase.patient?.notes ||
            (Array.isArray(symptoms) ? symptoms.join(', ') : symptoms) ||
            'Khám chuyên khoa theo định hướng AI';
          const item: BookingListItem = {
            id: foundCase.id,
            user_id: '',
            schedule_id: null,
            hold_id: null,
            doctor_id: foundCase.plan?.doctor_id || 'coordinator',
            facility_id: foundCase.plan?.facility_id || 'riverside',
            starts_at: startsAt,
            ends_at: startsAt,
            booking_mode: 'doctor_visit',
            service_id: foundCase.plan?.service_id || 'consultation',
            specialty_id: foundCase.plan?.specialty_id || 'ortho',
            encounter_type: 'in_person',
            reason,
            patient_note: `Phiếu điều phối AI: ${foundCase.patient?.name || ''} - SĐT: ${foundCase.patient?.phone || ''}`,
            status: statusMap[foundCase.status] || 'pending_approval',
            cancellation_reason: null,
            created_at: foundCase.created_at,
            updated_at: foundCase.created_at,
            coordinationCase: foundCase,
          };
          setBookingItem(item);
          setIsLoading(false);
          return;
        }

        setError('Không tìm thấy thông tin lịch hẹn hoặc gói khám này.');
      } catch {
        if (isMounted) setError('Không thể tải chi tiết lịch hẹn. Vui lòng thử lại.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    void loadAll();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const handleCancelConfirm = async () => {
    if (!bookingItem || bookingItem.status === 'cancelled' || isCancelling) return;
    setError('');
    setIsCancelling(true);
    try {
      const updated = await cancelBooking(bookingItem.id, cancelReason);
      setBookingItem((prev) => (prev ? { ...prev, ...(updated || {}), status: 'cancelled' } : null));
      setShowCancelDialog(false);
      setSuccessMessage('Đã hủy lịch hẹn thành công.');
    } catch {
      setError('Không thể hủy lúc này. Vui lòng kiểm tra lại trạng thái.');
    } finally {
      setIsCancelling(false);
    }
  };

  const openPackageReschedule = () => {
    const pkg = bookingItem?.packageRequest;
    const defaultDate = pkg?.preferred_date
      ? (pkg.preferred_date.includes('T') ? pkg.preferred_date.slice(0, 10) : pkg.preferred_date)
      : (bookingItem?.starts_at ? bookingItem.starts_at.slice(0, 10) : new Date().toISOString().slice(0, 10));
    setNewPackageDate(defaultDate);
    setNewPackagePeriod(pkg?.preferred_period || 'morning');
    setNewPackageFacilityId(pkg?.facility_id || bookingItem?.facility_id || '');
    setRescheduleNote('');
    setShowRescheduleDialog(true);
    setShowCancelDialog(false);
  };

  const handlePackageRescheduleSubmit = async () => {
    if (!bookingItem || isRescheduling) return;
    if (!newPackageDate) {
      setError('Vui lòng chọn ngày khám mới.');
      return;
    }
    setIsRescheduling(true);
    setError('');
    const targetRequestId = bookingItem.packageRequest?.id || bookingItem.id;
    try {
      const updated = await reschedulePackageRequest(targetRequestId, {
        preferred_date: newPackageDate,
        preferred_period: newPackagePeriod,
        facility_id: newPackageFacilityId || undefined,
        note: rescheduleNote.trim() || undefined,
      });

      const timeStr = newPackagePeriod === 'afternoon' ? 'T13:30:00+07:00' : 'T08:00:00+07:00';
      const newStartsAt = `${newPackageDate}${timeStr}`;
      setBookingItem((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          facility_id: newPackageFacilityId || prev.facility_id,
          starts_at: newStartsAt,
          ends_at: newStartsAt,
          packageRequest: updated,
        };
      });
      setShowRescheduleDialog(false);
      setSuccessMessage(
        `Đã đổi ngày khám cho gói thành công: ${formatDateOnlyVN(newPackageDate)} (${newPackagePeriod === 'morning' ? 'Buổi sáng' : 'Buổi chiều'})`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Không thể đổi ngày gói khám. Vui lòng thử lại.';
      setError(msg);
    } finally {
      setIsRescheduling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface text-emerald-800 dark:text-emerald-300 light:text-app-primary">
        <TypewriterLoader /> Đang tải chi tiết lịch hẹn...
      </div>
    );
  }

  if (!bookingItem) {
    return (
      <section className="mx-auto max-w-2xl space-y-4 py-8">
        <div className="rounded-2xl border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-6 text-center">
          <p className="text-sm text-slate-700 dark:text-slate-300">{error || 'Không tìm thấy lịch hẹn.'}</p>
          <div className="mt-4">
            <Link
              to="/patient/progress"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800 transition"
            >
              <ArrowLeft className="h-4 w-4" /> Quay lại danh sách lịch hẹn
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const display = getDisplayData(bookingItem, catalog);
  const isPackage = display.bookingType === 'package';
  const isDoctor = display.bookingType === 'doctor_visit';
  const canModify = bookingItem.status === 'pending_approval' || bookingItem.status === 'confirmed';

  return (
    <section className="mx-auto max-w-3xl space-y-5">
      {/* Nút Quay lại danh sách */}
      <div className="flex items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-app-border light:border-app-border">
        <button
          type="button"
          onClick={() => navigate('/patient/progress')}
          className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-app-text light:text-app-text hover:text-emerald-700 dark:hover:text-emerald-400 transition cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> Quay lại danh sách
        </button>
        <span className="font-mono text-xs text-slate-400 dark:text-app-secondary">
          #{bookingItem.id ? bookingItem.id.slice(0, 8).toUpperCase() : ''}
        </span>
      </div>

      {successMessage && (
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/50 px-4 py-3 text-xs text-emerald-800 dark:text-emerald-200 flex items-center justify-between">
          <span>{successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage('')} className="font-bold underline text-xs">
            Đóng
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/50 px-4 py-3 text-xs text-rose-800 dark:text-rose-200">
          {error}
        </div>
      )}

      {/* Thẻ Chi tiết chính */}
      <div className="rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-6 shadow-2xs space-y-6">
        {/* Header thông tin loại & tiêu đề */}
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-bold shadow-2xs',
                display.typeBadge.bg,
                display.typeBadge.text,
                display.typeBadge.border,
              )}
            >
              <span>{display.typeBadge.icon}</span>
              <span>{display.typeBadge.label}</span>
            </span>

            <span
              className={clsx('inline-flex rounded-full border px-3 py-0.5 text-xs font-bold', statusStyle(bookingItem.status))}
            >
              {statusLabel(bookingItem.status, display.bookingType)}
            </span>
          </div>

          <div className="mt-3 flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-slate-900 dark:text-app-text light:text-app-text sm:text-2xl">
                {display.primaryTitle}
              </h1>
              <p className="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                {display.secondaryTitle}
              </p>
            </div>

            <div className="shrink-0 rounded-xl p-3 border border-slate-200 dark:border-app-border bg-slate-50 dark:bg-app-surface">
              {isPackage ? (
                <Package className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              ) : isDoctor ? (
                <Stethoscope className="h-6 w-6 text-sky-600 dark:text-sky-400" />
              ) : (
                <UserRoundCheck className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
              )}
            </div>
          </div>
        </div>

        {/* Thanh Tiến trình chi tiết */}
        <HITLProgress status={bookingItem.status} progress={display.progress} />

        {/* Mã Check-in nếu đã xác nhận */}
        {bookingItem.status === 'confirmed' && (
          <div className="rounded-xl border border-teal-200 dark:border-teal-800 bg-teal-50/70 dark:bg-teal-950/40 p-4">
            <div className="flex items-center gap-3">
              <QrCode className="h-6 w-6 text-teal-700 dark:text-teal-300" />
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-teal-800 dark:text-teal-300">
                  Mã tiếp đón check-in
                </p>
                <p className="mt-0.5 font-mono text-base font-bold text-slate-900 dark:text-app-text">
                  #{bookingItem.id ? bookingItem.id.slice(0, 8).toUpperCase() : ''}
                </p>
              </div>
            </div>
            <p className="mt-2 text-xs text-teal-900 dark:text-teal-200">
              Xuất trình mã hoặc số điện thoại tại quầy lễ tân để được hỗ trợ tiếp đón ưu tiên.
            </p>
          </div>
        )}

        {/* Thông số lịch hẹn */}
        <div className="grid gap-3.5 rounded-xl border border-slate-100 dark:border-app-border light:border-app-border bg-slate-50 dark:bg-app-surface light:bg-app-page p-4 text-xs">
          {/* Thời gian */}
          <div className="flex gap-3">
            <CalendarClock className="mt-0.5 h-4.5 w-4.5 text-slate-600 dark:text-app-secondary shrink-0" />
            <div>
              <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">
                {isPackage ? 'Ngày & Buổi khám' : 'Thời gian hẹn'}
              </p>
              <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text">
                {display.startsAtFormatted}
              </p>
              {display.preferredPeriod && (
                <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                  {display.preferredPeriod === 'morning' ? 'Buổi sáng (07:30 - 11:30)' : 'Buổi chiều (13:30 - 17:00)'}
                </p>
              )}
            </div>
          </div>

          {/* Cơ sở */}
          <div className="flex gap-3">
            <MapPin className="mt-0.5 h-4.5 w-4.5 text-slate-600 dark:text-app-secondary shrink-0" />
            <div>
              <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">Cơ sở thực hiện</p>
              <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text">{display.facilityName}</p>
            </div>
          </div>

          {/* Dịch vụ & Chi phí */}
          {display.servicePrice !== undefined && display.servicePrice !== null && (
            <div className="flex gap-3">
              <CreditCard className="mt-0.5 h-4.5 w-4.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <div>
                <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">Chi phí tham khảo</p>
                <p className="mt-0.5 text-sm font-bold text-emerald-600 dark:text-emerald-400">
                  {display.servicePrice.toLocaleString('vi-VN')} đ
                </p>
              </div>
            </div>
          )}

          {/* Bác sĩ (nếu có) */}
          {isDoctor && display.doctorName && (
            <div className="flex gap-3">
              <Stethoscope className="mt-0.5 h-4.5 w-4.5 text-slate-600 dark:text-app-secondary shrink-0" />
              <div>
                <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">Bác sĩ phụ trách</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text">{display.doctorName}</p>
                {display.doctorTitle && (
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-app-secondary">{display.doctorTitle}</p>
                )}
              </div>
            </div>
          )}

          {/* Ghi chú / Triệu chứng */}
          {display.notes && (
            <div className="flex gap-3">
              <FileText className="mt-0.5 h-4.5 w-4.5 text-slate-600 dark:text-app-secondary shrink-0" />
              <div>
                <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">Ghi chú & Bệnh cảnh</p>
                <p className="mt-0.5 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{display.notes}</p>
              </div>
            </div>
          )}
        </div>

        {/* Dặn dò trước khám cốt lõi */}
        {display.instructions && display.instructions.length > 0 && (
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">
              {isPackage ? 'Chuẩn bị trước khi khám gói' : 'Dặn dò trước giờ khám'}
            </h2>
            <div className="mt-3 space-y-2">
              {display.instructions.map((inst, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 dark:border-app-border bg-slate-50/70 dark:bg-app-surface p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-app-text">
                      <span>{inst.icon || '📌'}</span>
                      <span>{inst.title}</span>
                    </div>
                    {inst.badge && (
                      <span className="rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 text-[10px] px-2 py-0.5 font-semibold">
                        {inst.badge}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-600 dark:text-app-secondary leading-relaxed pl-5">
                    {inst.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Nút thao tác Đổi lịch & Hủy lịch */}
        {canModify && (
          <div className="pt-4 border-t border-slate-100 dark:border-app-border flex flex-wrap items-center gap-3">
            {isPackage ? (
              <button
                type="button"
                onClick={openPackageReschedule}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2.5 text-xs font-bold transition cursor-pointer shadow-2xs"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Đổi ngày &amp; buổi khám gói
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  if (display.bookingType === 'coordination') {
                    navigate('/patient/appointments');
                  } else {
                    navigate(`/patient/appointments?reschedule=${bookingItem.id}`);
                  }
                }}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-100 dark:bg-app-muted hover:bg-slate-200 dark:hover:bg-app-muted/80 px-4 py-2.5 text-xs font-bold text-slate-700 dark:text-app-text transition cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Đổi lịch hẹn
              </button>
            )}

            {isPackage && (
              <Link
                to={`/patient/appointments?mode=package`}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-app-border bg-slate-50 dark:bg-app-surface hover:bg-slate-100 dark:hover:bg-app-muted px-3.5 py-2.5 text-xs font-bold text-slate-700 dark:text-app-text transition cursor-pointer"
              >
                Đăng ký gói khác →
              </Link>
            )}

            <button
              type="button"
              onClick={() => {
                setShowCancelDialog(true);
                setShowRescheduleDialog(false);
              }}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 dark:border-rose-800 px-4 py-2.5 text-xs font-bold text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
              {isPackage ? 'Hủy đăng ký gói' : 'Hủy lịch hẹn'}
            </button>
          </div>
        )}

        {/* Modal / Dialog Đổi ngày gói khám trực tiếp */}
        {showRescheduleDialog && (
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/60 dark:bg-emerald-950/40 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                Đổi ngày khám cho gói: <span className="font-extrabold">{display.primaryTitle}</span>
              </h3>
              <button
                type="button"
                onClick={() => setShowRescheduleDialog(false)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 text-xs">
              <div>
                <label className="block font-bold text-slate-700 dark:text-app-text mb-1">
                  Ngày khám mới mong muốn:
                </label>
                <DateInputVN
                  min={new Date().toISOString().slice(0, 10)}
                  value={newPackageDate}
                  onChange={(e) => setNewPackageDate(e.target.value)}
                  placeholder="dd/mm/yyyy"
                  className="w-full rounded-lg border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-2 text-xs text-slate-900 dark:text-app-text outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 dark:text-app-text mb-1">
                  Buổi khám:
                </label>
                <select
                  value={newPackagePeriod}
                  onChange={(e) => setNewPackagePeriod(e.target.value as 'morning' | 'afternoon')}
                  className="w-full rounded-lg border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-2 text-xs text-slate-900 dark:text-app-text outline-none focus:border-emerald-600"
                >
                  <option value="morning">Buổi sáng (07:30 - 11:30)</option>
                  <option value="afternoon">Buổi chiều (13:30 - 17:00)</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-bold text-slate-700 dark:text-app-text mb-1">
                  Cơ sở bệnh viện tiếp nhận:
                </label>
                <select
                  value={newPackageFacilityId}
                  onChange={(e) => setNewPackageFacilityId(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-2 text-xs text-slate-900 dark:text-app-text outline-none focus:border-emerald-600"
                >
                  {Array.from(catalog.facilities.values()).map((fac) => (
                    <option key={fac.id} value={fac.id}>
                      {fac.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 dark:text-app-text mb-1 text-xs">
                Ghi chú đổi ngày (không bắt buộc):
              </label>
              <input
                type="text"
                value={rescheduleNote}
                onChange={(e) => setRescheduleNote(e.target.value)}
                placeholder="Ví dụ: bận việc đột xuất, đổi sang tuần sau..."
                className="w-full rounded-lg border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-2 text-xs text-slate-900 dark:text-app-text outline-none focus:border-emerald-600"
              />
            </div>

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={handlePackageRescheduleSubmit}
                disabled={isRescheduling}
                className="rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800 disabled:opacity-50 transition cursor-pointer"
              >
                {isRescheduling ? 'Đang cập nhật...' : 'Xác nhận đổi ngày'}
              </button>
              <button
                type="button"
                onClick={() => setShowRescheduleDialog(false)}
                className="rounded-lg border border-slate-300 dark:border-app-border px-3 py-2 text-xs font-semibold text-slate-700 dark:text-app-text hover:bg-slate-100 dark:hover:bg-app-muted transition cursor-pointer"
              >
                Hủy bỏ
              </button>
            </div>
          </div>
        )}

        {/* Modal xác nhận hủy gọn gàng */}
        {showCancelDialog && (
          <div className="rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50/50 dark:bg-rose-950/40 p-4 space-y-3">
            <h3 className="text-xs font-bold text-rose-900 dark:text-rose-200">
              Xác nhận hủy {isPackage ? 'đăng ký gói khám' : 'lịch hẹn'}?
            </h3>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Nhập lý do hủy (không bắt buộc)..."
              rows={2}
              className="w-full rounded-lg border border-slate-200 dark:border-app-border bg-white dark:bg-app-surface p-2 text-xs text-slate-900 dark:text-app-text outline-none focus:border-rose-500"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCancelConfirm}
                disabled={isCancelling}
                className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700 disabled:opacity-50 transition cursor-pointer"
              >
                {isCancelling ? 'Đang hủy...' : 'Đồng ý hủy'}
              </button>
              <button
                type="button"
                onClick={() => setShowCancelDialog(false)}
                className="rounded-lg border border-slate-300 dark:border-app-border px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-app-text hover:bg-slate-100 dark:hover:bg-app-muted transition cursor-pointer"
              >
                Quay lại
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
