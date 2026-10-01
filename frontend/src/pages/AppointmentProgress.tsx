import { Loader2, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Booking,
  BookingApiError,
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
import { fetchCurrentUser, PatientProfile } from '../features/patient/api';
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

function getDisplayData(booking: Booking, catalog: AppointmentCatalog): AppointmentDisplayData {
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

const emptyCatalog: AppointmentCatalog = {
  doctors: new Map<string, Doctor>(),
  facilities: new Map<string, Facility>(),
  services: new Map<string, MedicalService>(),
  specialties: new Map<string, Specialty>(),
};

export default function AppointmentProgress() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [catalog, setCatalog] = useState<AppointmentCatalog>(emptyCatalog);
  const [filter, setFilter] = useState<AppointmentFilter>('all');
  const [selectedBookingId, setSelectedBookingId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [noticeVisible, setNoticeVisible] = useState(true);
  const [error, setError] = useState('');

  const loadData = async (showInitialLoader = false) => {
    if (showInitialLoader) setIsLoading(true);
    else setIsRefreshing(true);
    setError('');

    const [bookingResult, profileResult, doctorsResult, facilitiesResult, servicesResult, specialtiesResult] = await Promise.allSettled([
      fetchBookings(),
      fetchCurrentUser(),
      fetchDoctors(),
      fetchFacilities(),
      fetchServices(),
      fetchSpecialties(),
    ]);

    if (bookingResult.status === 'fulfilled') setBookings(bookingResult.value);
    else setError(bookingResult.reason instanceof BookingApiError && bookingResult.reason.status === 403
      ? 'Tài khoản hiện tại không có quyền xem lịch hẹn.'
      : 'Không thể tải lịch hẹn. Vui lòng thử lại.');

    if (profileResult.status === 'fulfilled') setProfile(profileResult.value);
    setCatalog({
      doctors: doctorsResult.status === 'fulfilled' ? toMap(doctorsResult.value) : new Map(),
      facilities: facilitiesResult.status === 'fulfilled' ? toMap(facilitiesResult.value) : new Map(),
      services: servicesResult.status === 'fulfilled' ? toMap(servicesResult.value) : new Map(),
      specialties: specialtiesResult.status === 'fulfilled' ? toMap(specialtiesResult.value) : new Map(),
    });

    setIsLoading(false);
    setIsRefreshing(false);
  };

  useEffect(() => {
    void loadData(true);
  }, []);

  const counts = useMemo<Record<AppointmentFilter, number>>(() => ({
    all: bookings.length,
    pending_approval: bookings.filter((booking) => booking.status === 'pending_approval').length,
    confirmed: bookings.filter((booking) => booking.status === 'confirmed').length,
    rejected: bookings.filter((booking) => booking.status === 'rejected').length,
    cancelled: bookings.filter((booking) => booking.status === 'cancelled').length,
    expired: bookings.filter((booking) => booking.status === 'expired').length,
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
    setIsCancelling(true);
    setError('');
    try {
      const updated = await cancelBooking(selectedBooking.id);
      setBookings((current) => current.map((booking) => booking.id === updated.id ? updated : booking));
    } catch {
      setError('Không thể hủy lịch hẹn lúc này. Vui lòng thử lại.');
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-slate-200 bg-white text-sky-700"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Đang tải tiến trình lịch hẹn...</div>;
  }

  return (
    <section className="space-y-6">
      <AppointmentProgressHeader patientId={profile?.id || 'unknown'} />

      <CoordinatorNotice message={noticeVisible ? noticeMessage : null} onDismiss={() => setNoticeVisible(false)} />

      {error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <AppointmentFilters value={filter} counts={counts} onChange={setFilter} />
        <button type="button" onClick={() => void loadData()} disabled={isRefreshing} className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:border-sky-300 hover:text-sky-700 disabled:cursor-wait disabled:opacity-60 xl:self-auto">
          <RefreshCw className={isRefreshing ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /> Làm mới
        </button>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)]">
        <div className="space-y-4">
          {filteredBookings.length === 0 && <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center text-sm text-slate-500">Không có lịch hẹn trong trạng thái này.</div>}
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
