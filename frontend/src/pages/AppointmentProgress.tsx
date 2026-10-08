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
  fetchMyPackageRequests,
  PackageRequest,
} from '../features/appointment-booking/api';

import { fetchCurrentUser, peekCurrentUser, PatientProfile } from '../features/patient/api';

import {
  AppointmentCard,
  AppointmentFilters,
  AppointmentProgressHeader,
} from '../features/appointment-progress/components';

import { AppointmentCatalog, AppointmentDisplayData, AppointmentFilter } from '../features/appointment-progress/types';



import {
  BookingListItem,
  getDisplayData,
  LiveCoordinationCase,
  toCatalogMap,
} from '../features/appointment-progress/utils';



const SNAPSHOT_KEY = 'treatment:bookings';

const VIEW_KEY = 'treatment:view';

const SNAPSHOT_TTL_MS = 5 * 60_000;

type SavedView = { filter: AppointmentFilter };

function cachedCatalog(): AppointmentCatalog {
  return {
    doctors: toCatalogMap(peekQuery<Doctor[]>('catalog:doctors:', true) || []),
    facilities: toCatalogMap(peekQuery<Facility[]>('catalog:facilities', true) || []),
    services: toCatalogMap(peekQuery<MedicalService[]>('catalog:services:', true) || []),
    specialties: toCatalogMap(peekQuery<Specialty[]>('catalog:specialties', true) || []),
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
  const [isLoading, setIsLoading] = useState(() => previousBookings === undefined);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadVersion = useRef(0);
  const mounted = useRef(false);

  const loadData = async (showInitialLoader = false, force = false) => {
    const version = ++loadVersion.current;
    if (showInitialLoader) setIsLoading(true);
    else setIsRefreshing(true);
    setError('');

    const [bookingResult, profileResult, doctorsResult, facilitiesResult, servicesResult, specialtiesResult, liveCasesResult, packageRequestsResult] = await Promise.allSettled([
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
      fetchMyPackageRequests().catch(() => []),
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
    const packageRequests: PackageRequest[] = packageRequestsResult.status === 'fulfilled' ? packageRequestsResult.value : [];
    const existingBookingIds = new Set(directBookings.map((b) => b.id));

    // Convert package registration requests into appointment items
    const packageBookings: BookingListItem[] = packageRequests.map((pr) => {
      const timeStr = pr.preferred_period === 'afternoon' ? 'T13:30:00+07:00' : 'T08:00:00+07:00';
      const startsAt = pr.preferred_date ? (pr.preferred_date.includes('T') ? pr.preferred_date : `${pr.preferred_date}${timeStr}`) : (pr.created_at || new Date().toISOString());
      const statusMap: Record<string, BookingStatus> = {
        pending: 'pending_approval',
        contacted: 'pending_approval',
        confirmed: 'confirmed',
        completed: 'confirmed',
        cancelled: 'cancelled',
      };
      return {
        id: pr.id,
        user_id: pr.patient_id || '',
        schedule_id: null,
        hold_id: null,
        doctor_id: '',
        facility_id: pr.facility_id,
        starts_at: startsAt,
        ends_at: startsAt,
        booking_mode: 'package',
        service_id: pr.service_id,
        specialty_id: '',
        encounter_type: 'in_person',
        reason: pr.note || `Đăng ký ${pr.service_name || 'Gói khám sức khỏe'}`,
        patient_note: pr.staff_note || null,
        status: statusMap[pr.status] || 'pending_approval',
        cancellation_reason: null,
        created_at: pr.created_at || startsAt,
        updated_at: pr.created_at || startsAt,
        packageRequest: pr,
      };
    });

    const packageRequestIds = new Set(packageRequests.map((pr) => pr.id));

    // Convert unmerged coordination cases into appointment items (exclude cases belonging to package requests)
    const caseBookings: BookingListItem[] = liveCases
      .filter((c) => {
        if (c.booking_id && existingBookingIds.has(c.booking_id)) return false;
        const src = (c as { source?: string }).source;
        const srcId = (c as { source_id?: string }).source_id;
        if (src === 'package') return false;
        if (srcId && packageRequestIds.has(srcId)) return false;
        return true;
      })
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

    const mappedDirectBookings: BookingListItem[] = directBookings.map((b) => {
      const s = servicesResult.status === 'fulfilled' ? servicesResult.value.find((svc) => svc.id === b.service_id) : undefined;
      const isGroup = b.booking_mode === 'group' || s?.booking_mode === 'group';
      return {
        ...b,
        booking_mode: isGroup ? 'package' : (b.booking_mode || 'doctor_visit'),
      };
    });

    const combinedBookings = [...packageBookings, ...caseBookings, ...mappedDirectBookings].sort((a, b) => {
      const da = new Date(a.starts_at || a.created_at || 0).getTime();
      const db = new Date(b.starts_at || b.created_at || 0).getTime();
      return db - da;
    });

    setBookings(combinedBookings);
    rememberQuery(SNAPSHOT_KEY, combinedBookings, SNAPSHOT_TTL_MS);

    if (profileResult.status === 'fulfilled') setProfile(profileResult.value);

    setCatalog((current) => ({
      doctors: doctorsResult.status === 'fulfilled' ? toCatalogMap(doctorsResult.value) : current.doctors,
      facilities: facilitiesResult.status === 'fulfilled' ? toCatalogMap(facilitiesResult.value) : current.facilities,
      services: servicesResult.status === 'fulfilled' ? toCatalogMap(servicesResult.value) : current.services,
      specialties: specialtiesResult.status === 'fulfilled' ? toCatalogMap(specialtiesResult.value) : current.specialties,
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
    rememberQuery<SavedView>(VIEW_KEY, { filter }, 30 * 60_000);
  }, [filter]);

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

  if (isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface text-emerald-800 dark:text-emerald-300 light:text-app-primary">
        <TypewriterLoader /> Đang tải danh sách lịch hẹn...
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <AppointmentProgressHeader patientId={profile?.id || 'unknown'} />

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 px-4 py-3 text-xs text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Filter Tabs & Refresh */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <AppointmentFilters value={filter} counts={counts} onChange={setFilter} />

        <button
          type="button"
          onClick={() => void loadData(false, true)}
          disabled={isRefreshing}
          className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-app-text hover:border-emerald-300 dark:hover:border-emerald-800 hover:text-emerald-700 dark:hover:text-emerald-300 disabled:cursor-wait disabled:opacity-60 sm:self-auto cursor-pointer transition shadow-2xs"
        >
          <RefreshCw className={isRefreshing ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} /> Làm mới
        </button>
      </div>

      {/* Danh sách thẻ lịch */}
      {filteredBookings.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-6 py-16 text-center text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">
          Không có lịch hẹn nào trong mục này.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredBookings.map((booking) => (
            <AppointmentCard
              key={booking.id}
              booking={booking}
              display={getDisplayData(booking, catalog)}
              onSelect={() => navigate(`/patient/progress/${booking.id}`)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

