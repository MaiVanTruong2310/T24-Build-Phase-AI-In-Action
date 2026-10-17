import { Visible } from '../features/uiVisibility/Visible'
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
import '../features/appointment-progress/progress.css';

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
          const svc = direct.service_id ? currentCatalog.services.get(direct.service_id) : undefined;
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
      <section className="ap apd" role="status" aria-label="Đang tải chi tiết lịch hẹn">
        <div className="apd-skel-top"><span className="ap-skel apd-skel--back" /></div>
        <div className="apd-cols" aria-hidden="true">
          <div className="apd-main">
            <div className="ap-card ap-card--skeleton"><span className="ap-skel ap-skel--w1" /><span className="ap-skel ap-skel--w2" /><span className="ap-skel ap-skel--w4" /></div>
            <div className="ap-card ap-card--skeleton"><span className="ap-skel ap-skel--w3" /><span className="ap-skel ap-skel--w3" /></div>
          </div>
        </div>
        <span className="sr-only">Đang tải chi tiết lịch hẹn…</span>
      </section>
    );
  }

  if (!bookingItem) {
    return (
      <section className="ap apd">
        <div role="alert" className="ap-empty">
          <span className="ap-empty__icon"><FileText size={30} aria-hidden="true" /></span>
          <p className="ap-empty__title">Không mở được lịch hẹn</p>
          <p>{error || 'Không tìm thấy lịch hẹn.'}</p>
          <Link to="/patient/progress" className="ap-btn ap-btn--primary"><ArrowLeft size={18} aria-hidden="true" /> Về danh sách lịch hẹn</Link>
        </div>
      </section>
    );
  }

  const display = getDisplayData(bookingItem, catalog);
  const isPackage = display.bookingType === 'package';
  const isDoctor = display.bookingType === 'doctor_visit';
  const canModify = bookingItem.status === 'pending_approval' || bookingItem.status === 'confirmed';
  const shortId = bookingItem.id ? bookingItem.id.slice(0, 8).toUpperCase() : '';
  const TypeIcon = isPackage ? Package : isDoctor ? Stethoscope : UserRoundCheck;

  return (
    <section className="ap apd">
      <div className="apd-top">
        <button type="button" className="ap-btn" onClick={() => navigate('/patient/progress')}>
          <ArrowLeft size={18} aria-hidden="true" /> Danh sách lịch hẹn
        </button>
        <span className="ap-code">#{shortId}</span>
      </div>

      {successMessage && (
        <div role="status" className="ap-note ap-note--ok">
          <span>{successMessage}</span>
          <button type="button" className="ap-btn" onClick={() => setSuccessMessage('')}>Đóng</button>
        </div>
      )}
      {error && <div role="alert" className="ap-note"><span>{error}</span></div>}

      <div className="apd-cols">
        <div className="apd-main">
          <header className="ap-card apd-hero">
            <div className="ap-card__top">
              <span className="ap-type"><span aria-hidden="true">{display.typeBadge.icon}</span>{display.typeBadge.label}</span>
              <span className={clsx('ap-status', `ap-status--${bookingItem.status}`)}>{statusLabel(bookingItem.status, display.bookingType)}</span>
            </div>
            <div className="ap-who">
              <span className="ap-avatar apd-avatar">
                {display.doctorAvatar ? <img src={display.doctorAvatar} alt="" referrerPolicy="no-referrer" /> : <TypeIcon size={28} aria-hidden="true" />}
              </span>
              <div className="ap-who__text">
                <h1 className="apd-title">{display.primaryTitle}</h1>
                <p className="apd-subtitle">{display.secondaryTitle}</p>
              </div>
            </div>
          </header>

          <HITLProgress status={bookingItem.status} progress={display.progress} />

          {bookingItem.status === 'confirmed' && (
            <div className="apd-ticket">
              <QrCode size={34} aria-hidden="true" />
              <div>
                <p className="apd-ticket__label">Mã tiếp đón check-in</p>
                <p className="apd-ticket__code">#{shortId}</p>
                <p className="apd-ticket__hint">Xuất trình mã hoặc số điện thoại tại quầy lễ tân để được hỗ trợ tiếp đón ưu tiên.</p>
              </div>
            </div>
          )}

          <Visible id="appointment_detail.info"><section className="ap-panel" aria-label="Thông tin lịch hẹn">
            <h2 className="ap-h2">Thông tin lịch hẹn</h2>
            <dl className="apd-facts">
              <div className="ap-fact">
                <CalendarClock size={18} aria-hidden="true" />
                <div>
                  <dt>{isPackage ? 'Ngày & buổi khám' : 'Thời gian hẹn'}</dt>
                  <dd>{display.startsAtFormatted}</dd>
                  {display.preferredPeriod && <dd className="apd-sub">{display.preferredPeriod === 'morning' ? 'Buổi sáng (07:30 - 11:30)' : 'Buổi chiều (13:30 - 17:00)'}</dd>}
                </div>
              </div>
              <div className="ap-fact">
                <MapPin size={18} aria-hidden="true" />
                <div><dt>Cơ sở thực hiện</dt><dd>{display.facilityName}</dd></div>
              </div>
              {display.servicePrice !== undefined && display.servicePrice !== null && (
                <div className="ap-fact">
                  <CreditCard size={18} aria-hidden="true" />
                  <div><dt>Chi phí tham khảo</dt><dd>{display.servicePrice.toLocaleString('vi-VN')} đ</dd></div>
                </div>
              )}
              {isDoctor && display.doctorName && (
                <div className="ap-fact">
                  <Stethoscope size={18} aria-hidden="true" />
                  <div><dt>Bác sĩ phụ trách</dt><dd>{display.doctorName}</dd>{display.doctorTitle && <dd className="apd-sub">{display.doctorTitle}</dd>}</div>
                </div>
              )}
              {display.notes && (
                <div className="ap-fact">
                  <FileText size={18} aria-hidden="true" />
                  <div><dt>Ghi chú & bệnh cảnh</dt><dd className="apd-notes">{display.notes}</dd></div>
                </div>
              )}
            </dl>
          </section></Visible>

          {display.instructions && display.instructions.length > 0 && (
            <Visible id="appointment_detail.instructions"><section className="ap-panel" aria-label="Dặn dò trước khám">
              <h2 className="ap-h2">{isPackage ? 'Chuẩn bị trước khi khám gói' : 'Dặn dò trước giờ khám'}</h2>
              <ul className="apd-notes-list">
                {display.instructions.map((inst, idx) => (
                  <li key={idx} className="apd-inst">
                    <div className="apd-inst__head">
                      <span><span aria-hidden="true">{inst.icon || '📌'}</span> {inst.title}</span>
                      {inst.badge && <em className="apd-inst__badge">{inst.badge}</em>}
                    </div>
                    <p>{inst.content}</p>
                  </li>
                ))}
              </ul>
            </section></Visible>
          )}
        </div>

        {canModify && (
          <Visible id="appointment_detail.actions"><aside className="apd-side" aria-label="Thao tác với lịch hẹn">
            <section className="ap-panel">
              <h2 className="ap-h2">Thao tác</h2>
              <div className="apd-actions">
                {isPackage ? (
                  <button type="button" className="ap-btn ap-btn--primary" onClick={openPackageReschedule}>
                    <RefreshCw size={16} aria-hidden="true" /> Đổi ngày &amp; buổi khám gói
                  </button>
                ) : (
                  <button
                    type="button"
                    className="ap-btn ap-btn--primary"
                    onClick={() => {
                      if (display.bookingType === 'coordination') {
                        navigate('/patient/appointments');
                      } else {
                        navigate(`/patient/appointments?reschedule=${bookingItem.id}`);
                      }
                    }}
                  >
                    <RefreshCw size={16} aria-hidden="true" /> Đổi lịch hẹn
                  </button>
                )}
                {isPackage && <Link to="/patient/appointments?mode=package" className="ap-btn">Đăng ký gói khác →</Link>}
                <button type="button" className="ap-btn ap-btn--danger" onClick={() => { setShowCancelDialog(true); setShowRescheduleDialog(false); }}>
                  <X size={16} aria-hidden="true" /> {isPackage ? 'Hủy đăng ký gói' : 'Hủy lịch hẹn'}
                </button>
              </div>

              {showRescheduleDialog && (
                <div className="apd-form" role="group" aria-label="Đổi ngày khám gói">
                  <div className="apd-form__head">
                    <h3>Đổi ngày khám: {display.primaryTitle}</h3>
                    <button type="button" className="apd-x" aria-label="Đóng" onClick={() => setShowRescheduleDialog(false)}><X size={16} aria-hidden="true" /></button>
                  </div>
                  <label className="apd-field"><span>Ngày khám mới mong muốn</span>
                    <DateInputVN
                      min={new Date().toISOString().slice(0, 10)}
                      value={newPackageDate}
                      onChange={(e) => setNewPackageDate(e.target.value)}
                      placeholder="dd/mm/yyyy"
                      className="apd-input"
                    />
                  </label>
                  <label className="apd-field"><span>Buổi khám</span>
                    <select className="apd-input" value={newPackagePeriod} onChange={(e) => setNewPackagePeriod(e.target.value as 'morning' | 'afternoon')}>
                      <option value="morning">Buổi sáng (07:30 - 11:30)</option>
                      <option value="afternoon">Buổi chiều (13:30 - 17:00)</option>
                    </select>
                  </label>
                  <label className="apd-field"><span>Cơ sở tiếp nhận</span>
                    <select className="apd-input" value={newPackageFacilityId} onChange={(e) => setNewPackageFacilityId(e.target.value)}>
                      {Array.from(catalog.facilities.values()).map((fac) => (<option key={fac.id} value={fac.id}>{fac.name}</option>))}
                    </select>
                  </label>
                  <label className="apd-field"><span>Ghi chú đổi ngày (không bắt buộc)</span>
                    <input type="text" className="apd-input" value={rescheduleNote} onChange={(e) => setRescheduleNote(e.target.value)} placeholder="Ví dụ: bận việc đột xuất, đổi sang tuần sau..." />
                  </label>
                  <div className="apd-form__btns">
                    <button type="button" className="ap-btn ap-btn--primary" onClick={handlePackageRescheduleSubmit} disabled={isRescheduling}>{isRescheduling ? 'Đang cập nhật...' : 'Xác nhận đổi ngày'}</button>
                    <button type="button" className="ap-btn" onClick={() => setShowRescheduleDialog(false)}>Hủy bỏ</button>
                  </div>
                </div>
              )}

              {showCancelDialog && (
                <div className="apd-form apd-form--danger" role="group" aria-label="Xác nhận hủy">
                  <h3>Xác nhận hủy {isPackage ? 'đăng ký gói khám' : 'lịch hẹn'}?</h3>
                  <label className="apd-field"><span>Lý do hủy (không bắt buộc)</span>
                    <textarea className="apd-input" rows={2} value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} placeholder="Nhập lý do hủy..." />
                  </label>
                  <div className="apd-form__btns">
                    <button type="button" className="ap-btn ap-btn--danger-solid" onClick={handleCancelConfirm} disabled={isCancelling}>{isCancelling ? 'Đang hủy...' : 'Đồng ý hủy'}</button>
                    <button type="button" className="ap-btn" onClick={() => setShowCancelDialog(false)}>Quay lại</button>
                  </div>
                </div>
              )}
            </section>
          </aside></Visible>
        )}
      </div>
    </section>
  );
}
