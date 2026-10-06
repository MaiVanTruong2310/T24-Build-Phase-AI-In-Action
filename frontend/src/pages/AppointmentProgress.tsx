import { TypewriterLoader } from '../components/TypewriterLoader';
import { RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '../app/apiClient';
import { cachedQuery, peekQuery, rememberQuery } from '../app/queryCache';
import {
  Booking,
  BookingApiError,
  BookingStatus,
  Doctor,
  Facility,
  fetchBookings,
  fetchDoctors,
  fetchFacilities,
  fetchServices,
  fetchSpecialties,
  MedicalService,
  Specialty,
  cancelBooking,
} from '../features/appointment-booking/api';

import { fetchCurrentUser, peekCurrentUser, PatientProfile } from '../features/patient/api';

import {

  AppointmentCard,

  AppointmentDetailPanel,

  AppointmentFilters,

  AppointmentProgressHeader,

  CoordinatorNotice,

  HitlTrustBadge,

} from '../features/appointment-progress/components';

import { AppointmentCatalog, AppointmentDisplayData, AppointmentFilter } from '../features/appointment-progress/types';



function toMap<T extends { id: string }>(items: T[]): Map<string, T> {

  return new Map(items.map((item) => [item.id, item]));

}



interface LiveCoordinationCase {
  id: string;
  booking_id: string | null;
  status: string;
  created_at: string;
  patient?: {
    name?: string | null;
    phone?: string | null;
    doctor_name?: string | null;
    notes?: string | null;
    preferred_date?: string | null;
    preferred_period?: 'morning' | 'afternoon' | null;
    facility_preference?: string | null;
  };
  plan?: {
    doctor_id?: string | null;
    facility_id?: string | null;
    service_id?: string | null;
    specialty_id?: string | null;
    specialty_name?: string | null;
  };
  ai_snapshot?: {
    symptoms?: string | string[] | null;
    suggested_department_name?: string | null;
  };
}

type BookingListItem = Booking & { coordinationCase?: LiveCoordinationCase };

function getDisplayData(booking: BookingListItem, catalog: AppointmentCatalog): AppointmentDisplayData {
  const coord = booking.coordinationCase;
  if (coord) {
    const p = coord.patient || {};
    const ai = coord.ai_snapshot || {};
    return {
      doctorName: p.doctor_name || 'Điều phối viên y tế sắp xếp bác sĩ phù hợp nhất',
      doctorTitle: 'Trợ lý y tế / Điều phối viên',
      doctorAvatar: null,
      specialtyName: ai.suggested_department_name || coord.plan?.specialty_name || 'Chuyên khoa phù hợp',
      serviceName: 'Đăng ký khám qua Trợ lý AI (Điều phối)',
      facilityName: p.facility_preference || 'Bệnh viện ĐKQT Vinmec Riverside',
    };
  }

  const doctor = catalog.doctors.get(booking.doctor_id);
  const facility = catalog.facilities.get(booking.facility_id);
  const service = catalog.services.get(booking.service_id);
  const specialty = catalog.specialties.get(booking.specialty_id);

  return {
    doctorName: doctor?.full_name || `Bác sĩ #${booking.doctor_id.slice(0, 8).toUpperCase()}`,
    doctorTitle: doctor?.title || '',
    doctorAvatar: doctor?.avatar_url || null,
    specialtyName: specialty?.name || 'Chuyên khoa đang cập nhật',
    serviceName: service?.name || 'Dịch vụ đang cập nhật',
    facilityName: facility?.name || `Cơ sở #${booking.facility_id.slice(0, 8).toUpperCase()}`,
  };
}



const SNAPSHOT_KEY = 'treatment:bookings';

const VIEW_KEY = 'treatment:view';

const SNAPSHOT_TTL_MS = 5 * 60_000;

type SavedView = { filter: AppointmentFilter; selectedBookingId: string; noticeVisible: boolean };



function cachedCatalog(): AppointmentCatalog {

  return {

    doctors: toMap(peekQuery<Doctor[]>('catalog:doctors:', true) || []),

    facilities: toMap(peekQuery<Facility[]>('catalog:facilities', true) || []),

    services: toMap(peekQuery<MedicalService[]>('catalog:services:', true) || []),

    specialties: toMap(peekQuery<Specialty[]>('catalog:specialties', true) || []),

  };

}



export default function AppointmentProgress() {

  const navigate = useNavigate();

  const previousBookings = peekQuery<BookingListItem[]>(SNAPSHOT_KEY);
  const hadCachedBookings = useRef(previousBookings !== undefined);

  const previousView = peekQuery<SavedView>(VIEW_KEY);

  const [profile, setProfile] = useState<PatientProfile | null>(() => peekCurrentUser() ?? null);

  const [bookings, setBookings] = useState<BookingListItem[]>(() => previousBookings ?? []);

  const [catalog, setCatalog] = useState<AppointmentCatalog>(cachedCatalog);

  const [filter, setFilter] = useState<AppointmentFilter>(() => previousView?.filter ?? 'all');

  const [selectedBookingId, setSelectedBookingId] = useState(() => previousView?.selectedBookingId ?? '');

  const [isLoading, setIsLoading] = useState(() => previousBookings === undefined);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const [isCancelling, setIsCancelling] = useState(false);

  const [noticeVisible, setNoticeVisible] = useState(() => previousView?.noticeVisible ?? true);

  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadVersion = useRef(0);

  const mounted = useRef(false);



  const loadData = async (showInitialLoader = false, force = false) => {

    const version = ++loadVersion.current;

    if (showInitialLoader) setIsLoading(true);

    else setIsRefreshing(true);

    setError('');



    const [bookingResult, profileResult, doctorsResult, facilitiesResult, servicesResult, specialtiesResult, liveCasesResult] = await Promise.allSettled([
      force ? fetchBookings() : cachedQuery('treatment:bookings-request', 0, fetchBookings),
      fetchCurrentUser(),
      fetchDoctors(),
      fetchFacilities(),
      fetchServices(),
      fetchSpecialties(),
      fetchWithAuth('/coordination/live/mine').then(async (res) => {
        if (!res.ok) return [];
        const json = await res.json();
        const result = json.data as unknown;
        return Array.isArray(result) ? (result as LiveCoordinationCase[]) : [];
      }),
    ]);

    if (!mounted.current || version !== loadVersion.current) return;

    let directBookings: Booking[] = [];
    if (bookingResult.status === 'fulfilled') {
      directBookings = bookingResult.value;
    } else {
      const status = bookingResult.reason instanceof BookingApiError ? bookingResult.reason.status : null;
      if (status === 401 || status === 403) {
        directBookings = [];
      } else {
        setError(status === 403
          ? 'Tài khoản hiện tại không có quyền xem lịch hẹn.'
          : 'Không thể tải lịch hẹn. Vui lòng thử lại.');
      }
    }

    const liveCases: LiveCoordinationCase[] = liveCasesResult.status === 'fulfilled' ? liveCasesResult.value : [];
    const existingBookingIds = new Set(directBookings.map((b) => b.id));

    // Convert unmerged coordination cases into appointment items
    const caseBookings: BookingListItem[] = liveCases
      .filter((c) => !c.booking_id || !existingBookingIds.has(c.booking_id))
      .map((c) => {
        const prefDate = c.patient?.preferred_date;
        const prefPeriod = c.patient?.preferred_period;
        const timeStr = prefPeriod === 'afternoon' ? 'T13:30:00+07:00' : 'T08:30:00+07:00';
        const startsAt = prefDate ? (prefDate.includes('T') ? prefDate : `${prefDate}${timeStr}`) : c.created_at;
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
        const symptoms = c.ai_snapshot?.symptoms;
        const reason = c.patient?.notes || (Array.isArray(symptoms) ? symptoms.join(', ') : symptoms) || 'Khám chuyên khoa theo định hướng AI';
        const caseBooking: BookingListItem = {
          id: c.id,
          user_id: '',
          schedule_id: null,
          hold_id: null,
          doctor_id: c.plan?.doctor_id || 'coordinator',
          facility_id: c.plan?.facility_id || 'riverside',
          starts_at: startsAt,
          ends_at: startsAt,
          booking_mode: 'doctor_visit',
          service_id: c.plan?.service_id || 'consultation',
          specialty_id: c.plan?.specialty_id || 'ortho',
          encounter_type: 'in_person',
          reason,
          patient_note: `Phiếu điều phối AI: ${c.patient?.name || ''} - SĐT: ${c.patient?.phone || ''} - Cơ sở: ${c.patient?.facility_preference || 'Vinmec Riverside'}`,
          status: statusMap[c.status] || 'pending_approval',
          cancellation_reason: null,
          created_at: c.created_at,
          updated_at: c.created_at,
          coordinationCase: c,
        };
        return caseBooking;
      });

    const combinedBookings = [...caseBookings, ...directBookings].sort((a, b) => {
      const da = new Date(a.starts_at || a.created_at || 0).getTime();
      const db = new Date(b.starts_at || b.created_at || 0).getTime();
      return db - da;
    });

    setBookings(combinedBookings);
    rememberQuery(SNAPSHOT_KEY, combinedBookings, SNAPSHOT_TTL_MS);



    if (profileResult.status === 'fulfilled') setProfile(profileResult.value);

    setCatalog((current) => ({

      doctors: doctorsResult.status === 'fulfilled' ? toMap(doctorsResult.value) : current.doctors,

      facilities: facilitiesResult.status === 'fulfilled' ? toMap(facilitiesResult.value) : current.facilities,

      services: servicesResult.status === 'fulfilled' ? toMap(servicesResult.value) : current.services,

      specialties: specialtiesResult.status === 'fulfilled' ? toMap(specialtiesResult.value) : current.specialties,

    }));



    setIsLoading(false);

    setIsRefreshing(false);

  };



  useEffect(() => {

    mounted.current = true;

    void loadData(!hadCachedBookings.current);

    return () => { mounted.current = false; loadVersion.current += 1; };

  }, []);



  useEffect(() => {

    rememberQuery<SavedView>(VIEW_KEY, { filter, selectedBookingId, noticeVisible }, 30 * 60_000);

  }, [filter, selectedBookingId, noticeVisible]);



  const counts = useMemo<Record<AppointmentFilter, number>>(() => ({

    all: bookings.length,

    pending_approval: bookings.filter((booking) => booking.status === 'pending_approval').length,

    confirmed: bookings.filter((booking) => booking.status === 'confirmed').length,

    rejected: bookings.filter((booking) => booking.status === 'rejected').length,

    cancelled: bookings.filter((booking) => booking.status === 'cancelled').length,

  }), [bookings]);



  const filteredBookings = useMemo(

    () => filter === 'all' ? bookings : bookings.filter((booking) => booking.status === filter),

    [bookings, filter],

  );



  useEffect(() => {

    if (!filteredBookings.some((booking) => booking.id === selectedBookingId)) {

      setSelectedBookingId(filteredBookings[0]?.id || '');

    }

  }, [filteredBookings, selectedBookingId]);



  const selectedBooking = bookings.find((booking) => booking.id === selectedBookingId) || null;

  const selectedDisplay = selectedBooking ? getDisplayData(selectedBooking, catalog) : null;

  const latestConfirmed = bookings.find((booking) => booking.status === 'confirmed');

  const noticeMessage = latestConfirmed

    ? `Lịch hẹn ngày ${new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit' }).format(new Date(latestConfirmed.starts_at))} đã được hệ thống ghi nhận. Vui lòng xem chi tiết để chuẩn bị trước khám.`

    : null;



  const handleCancel = async () => {
    if (!selectedBooking || isCancelling || !window.confirm('Bạn có chắc muốn hủy lịch hẹn này?')) return;
    loadVersion.current += 1;
    setIsRefreshing(false);
    setIsCancelling(true);
    setError('');
    setSuccessMessage('');
    try {
      const targetId = selectedBooking.id;
      const updated = await cancelBooking(targetId);
      const nextBookings = bookings.map((booking) => {
        if (booking.id === targetId || (updated && booking.id === updated.id)) {
          return {
            ...booking,
            ...(updated || {}),
            status: 'cancelled' as const,
          };
        }
        return booking;
      });
      setBookings(nextBookings);
      rememberQuery(SNAPSHOT_KEY, nextBookings, SNAPSHOT_TTL_MS);
      setFilter('cancelled');
      setSelectedBookingId(targetId);
      setSuccessMessage('Lịch hẹn đã được hủy thành công và chuyển vào mục "Đã hủy".');
    } catch {
      setError('Không thể hủy lịch hẹn lúc này. Vui lòng thử lại.');
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface text-sky-700 dark:text-sky-300 light:text-app-primary"><TypewriterLoader /> Đang tải tiến trình lịch hẹn...</div>;
  }

  return (
    <section className="space-y-6">
      <AppointmentProgressHeader patientId={profile?.id || 'unknown'} />

      <CoordinatorNotice message={noticeVisible ? noticeMessage : null} onDismiss={() => setNoticeVisible(false)} />

      {error && <div role="alert" className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}

      {successMessage && (
        <div role="status" className="flex items-center justify-between rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/50 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
          <span>{successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage('')} className="text-xs font-bold underline hover:text-emerald-900 dark:hover:text-emerald-100">Đóng</button>
        </div>
      )}



      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">

        <AppointmentFilters value={filter} counts={counts} onChange={setFilter} />

        <button type="button" onClick={() => void loadData(false, true)} disabled={isRefreshing} className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-4 py-2 text-sm font-semibold text-slate-600 dark:text-app-secondary light:text-app-secondary hover:border-sky-300 dark:hover:border-sky-800 hover:text-sky-700 dark:hover:text-sky-300 light:hover:text-app-primary disabled:cursor-wait disabled:opacity-60 xl:self-auto">

          <RefreshCw className={isRefreshing ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /> Làm mới

        </button>

      </div>



      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)]">

        <div className="space-y-4">

          {filteredBookings.length === 0 && <div className="rounded-3xl border border-dashed border-slate-300 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-6 py-16 text-center text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">Không có lịch hẹn trong trạng thái này.</div>}

          {filteredBookings.map((booking) => (

            <AppointmentCard

              key={booking.id}

              booking={booking}

              display={getDisplayData(booking, catalog)}

              selected={booking.id === selectedBookingId}

              onSelect={() => setSelectedBookingId(booking.id)}

            />

          ))}

        </div>

        <AppointmentDetailPanel

          booking={selectedBooking}

          display={selectedDisplay}

          isCancelling={isCancelling}

          onCancel={() => void handleCancel()}

          onReschedule={() => selectedBooking && navigate(`/patient/appointments?reschedule=${selectedBooking.id}`)}

        />

      </div>



      <div className="flex justify-end"><HitlTrustBadge /></div>

    </section>

  );

}

