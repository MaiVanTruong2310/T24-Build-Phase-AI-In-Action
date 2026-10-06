import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import type { RootState } from '../app/store';
import { AUTH_TOKENS_UPDATED_EVENT, readPublishedSession } from '../features/auth/session';

import { BookingHeader } from '../features/appointment-booking/components/BookingHeader';
import { BookingSummary } from '../features/appointment-booking/components/BookingSummary';
import { DateTimeSelector } from '../features/appointment-booking/components/DateTimeSelector';
import { DoctorCard } from '../features/appointment-booking/components/DoctorCard';
import { SpecialtySelector } from '../features/appointment-booking/components/SpecialtySelector';
import {
  BookingApiError,
  Booking,
  BookingHold,
  createBooking,
  createBookingHold,
  Doctor,
  Facility,
  fetchAvailability,
  fetchDoctors,
  fetchFacilities,
  fetchServices,
  fetchSpecialties,
  fetchBooking,
  MedicalService,
  releaseBookingHold,
  rescheduleBooking,
  Schedule,
  Specialty,
} from '../features/appointment-booking/api';

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

type BookingDraft = {
  userId: string;
  specialtyId: string;
  facilityId: string;
  serviceId: string;
  doctorId: string;
  date: string;
  type: 'offline' | 'telehealth';
  reason: string;
  patientNote: string;
};

// Route navigation unmounts this page. Keep the form in memory for this tab;
// holds and selected slots are deliberately not restored because they expire.
let bookingDraft: BookingDraft | null = null;
if (typeof window !== 'undefined') {
  window.addEventListener(AUTH_TOKENS_UPDATED_EVENT, () => {
    if (!readPublishedSession()) bookingDraft = null;
  });
}

export default function AppointmentBooking() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const rescheduleId = searchParams.get('reschedule');
  const patient = useSelector((state: RootState) => state.auth.user);
  const savedDraft = bookingDraft?.userId === patient?.id && !rescheduleId ? bookingDraft : null;
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState(() => savedDraft?.specialtyId ?? '');
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState(() => savedDraft?.facilityId ?? '');
  const [services, setServices] = useState<MedicalService[]>([]);
  const [selectedService, setSelectedService] = useState(() => savedDraft?.serviceId ?? '');
  const [loadingServices, setLoadingServices] = useState(false);

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState(() => savedDraft?.doctorId ?? '');
  const [loadingDoctors, setLoadingDoctors] = useState(false);

  const [selectedDate, setSelectedDate] = useState(() => savedDraft?.date && savedDraft.date >= formatLocalDate(new Date()) ? savedDraft.date : formatLocalDate(new Date()));
  const [selectedType, setSelectedType] = useState<'offline' | 'telehealth'>(() => savedDraft?.type ?? 'offline');
  const [selectedSlot, setSelectedSlot] = useState('');
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loadingAvailability, setLoadingAvailability] = useState(false);

  const [isBooking, setIsBooking] = useState(false);
  const [hold, setHold] = useState<BookingHold | null>(null);
  const [holdSecondsRemaining, setHoldSecondsRemaining] = useState(0);
  const [bookingError, setBookingError] = useState('');
  const [catalogError, setCatalogError] = useState('');
  const [availabilityError, setAvailabilityError] = useState('');
  const [reason, setReason] = useState(() => savedDraft?.reason ?? '');
  const [patientNote, setPatientNote] = useState(() => savedDraft?.patientNote ?? '');
  const [rescheduleSource, setRescheduleSource] = useState<Booking | null>(null);
  const [rescheduleLoading, setRescheduleLoading] = useState(false);
  const holdRef = useRef<BookingHold | null>(null);
  const idempotencyKeyRef = useRef<string | null>(null);
  const bookingCompletedRef = useRef(false);
  const previousServiceFilter = useRef<string | null>(null);
  const previousDoctorFilter = useRef<string | null>(null);

  useEffect(() => {
    if (!patient?.id || rescheduleId || bookingCompletedRef.current) return;
    bookingDraft = {
      userId: patient.id,
      specialtyId: selectedSpecialty,
      facilityId: selectedFacility,
      serviceId: selectedService,
      doctorId: selectedDoctorId,
      date: selectedDate,
      type: selectedType,
      reason,
      patientNote,
    };
  }, [patient?.id, rescheduleId, selectedSpecialty, selectedFacility, selectedService, selectedDoctorId, selectedDate, selectedType, reason, patientNote]);

  useEffect(() => {
    holdRef.current = hold;
  }, [hold]);

  useEffect(() => {
    return () => {
      const activeHold = holdRef.current;
      if (activeHold) void releaseBookingHold(activeHold.id).catch(() => undefined);
    };
  }, []);

  useEffect(() => {
    const previousHold = holdRef.current;
    if (previousHold) {
      holdRef.current = null;
      setHold(null);
      void releaseBookingHold(previousHold.id).catch(() => undefined);
    }
    let cancelled = false;

    Promise.all([fetchSpecialties(), fetchFacilities()])
      .then(([specialtyData, facilityData]) => {
        if (cancelled) return;
        setSpecialties(specialtyData);
        setFacilities(facilityData);
        setSelectedSpecialty((current) => current || specialtyData[0]?.id || '');
        setSelectedFacility((current) => current || facilityData[0]?.id || '');
      })
      .catch(() => {
        if (!cancelled) setCatalogError('Không thể tải danh mục khám. Vui lòng tải lại trang và thử lại.');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!rescheduleId) {
      setRescheduleSource(null);
      return;
    }
    let cancelled = false;
    setRescheduleLoading(true);
    fetchBooking(rescheduleId)
      .then((booking) => {
        if (cancelled) return;
        setRescheduleSource(booking);
        setSelectedSpecialty(booking.specialty_id);
        setSelectedFacility(booking.facility_id);
        setSelectedDoctorId(booking.doctor_id);
        setSelectedService(booking.service_id);
        setSelectedDate(formatLocalDate(new Date(booking.starts_at)));
        setSelectedType(booking.encounter_type === 'in_person' ? 'offline' : 'telehealth');
        setReason(booking.reason);
        setPatientNote(booking.patient_note || '');
      })
      .catch(() => setBookingError('Không thể tải lịch hẹn cần đổi. Vui lòng quay lại lịch sử.'))
      .finally(() => {
        if (!cancelled) setRescheduleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [rescheduleId]);

  useEffect(() => {
    let cancelled = false;
    setServices([]);
    const filter = `${selectedSpecialty}:${selectedFacility}`;
    if (previousServiceFilter.current !== null && previousServiceFilter.current !== filter) setSelectedService('');
    previousServiceFilter.current = filter;
    setCatalogError('');

    if (!selectedSpecialty) {
      setSelectedService('');
      setLoadingServices(false);
      return () => {
        cancelled = true;
      };
    }

    setLoadingServices(true);
    fetchServices({
      specialtyId: selectedSpecialty,
      facilityId: selectedFacility || undefined,
    })
      .then((data) => {
        if (cancelled) return;
        setServices(data);
        const preferredService = rescheduleSource?.service_id;
        setSelectedService((current) => current && data.some((item) => item.id === current)
          ? current
          : preferredService && data.some((item) => item.id === preferredService) ? preferredService : data[0]?.id || '');
      })
      .catch(() => {
        if (!cancelled) setCatalogError('Không thể tải dịch vụ phù hợp với chuyên khoa và cơ sở đã chọn.');
      })
      .finally(() => {
        if (!cancelled) setLoadingServices(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSpecialty, selectedFacility, rescheduleSource?.service_id]);

  useEffect(() => {
    let cancelled = false;
    setDoctors([]);
    const filter = `${selectedSpecialty}:${selectedFacility}:${selectedService}`;
    if (previousDoctorFilter.current !== null && previousDoctorFilter.current !== filter) setSelectedDoctorId('');
    previousDoctorFilter.current = filter;
    setSchedules([]);
    setSelectedSlot('');
    setAvailabilityError('');

    if (!selectedSpecialty || !selectedService) {
      setSelectedDoctorId('');
      setLoadingDoctors(false);
      return () => {
        cancelled = true;
      };
    }

    setLoadingDoctors(true);
    fetchDoctors({
      specialtyId: selectedSpecialty,
      facilityId: selectedFacility || undefined,
      serviceId: selectedService,
      bookingEnabled: true,
    })
      .then((data) => {
        if (cancelled) return;
        setDoctors(data);
        const preferredDoctor = rescheduleSource?.doctor_id;
        setSelectedDoctorId((current) => current && data.some((item) => item.id === current)
          ? current
          : preferredDoctor && data.some((item) => item.id === preferredDoctor) ? preferredDoctor : data[0]?.id || '');
      })
      .catch(() => {
        if (!cancelled) setBookingError('Không thể tải danh sách bác sĩ. Vui lòng thử lại.');
      })
      .finally(() => {
        if (!cancelled) setLoadingDoctors(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSpecialty, selectedFacility, selectedService, rescheduleSource?.doctor_id]);

  useEffect(() => {
    const previousHold = holdRef.current;
    if (!previousHold) return;
    holdRef.current = null;
    setHold(null);
    void releaseBookingHold(previousHold.id).catch(() => undefined);
  }, [selectedDoctorId, selectedDate]);

  useEffect(() => {
    if (!hold) {
      setHoldSecondsRemaining(0);
      return undefined;
    }

    const updateRemaining = () => {
      const seconds = Math.max(0, Math.ceil((new Date(hold.expires_at).getTime() - Date.now()) / 1000));
      setHoldSecondsRemaining(seconds);
      if (seconds === 0) {
        holdRef.current = null;
        setHold(null);
        setSelectedSlot('');
        setBookingError('Thời gian giữ chỗ đã hết. Vui lòng chọn lại khung giờ.');
      }
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timer);
  }, [hold]);

  useEffect(() => {
    let cancelled = false;
    setSchedules([]);
    setSelectedSlot('');
    setAvailabilityError('');

    if (!selectedDoctorId || !selectedDate) {
      setLoadingAvailability(false);
      return () => {
        cancelled = true;
      };
    }

    setLoadingAvailability(true);
    fetchAvailability(selectedDoctorId, selectedDate, selectedFacility || undefined, selectedService || undefined)
      .then((data) => {
        if (cancelled) return;
        setSchedules(data);
        // Require an explicit slot selection so the chosen time is always visible to the patient.
        setSelectedSlot('');
      })
      .catch(() => {
        if (!cancelled) setAvailabilityError('Không thể tải khung giờ. Vui lòng chọn ngày khác hoặc thử lại.');
      })
      .finally(() => {
        if (!cancelled) setLoadingAvailability(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDoctorId, selectedDate, selectedFacility, selectedService]);

  const selectedSpecialtyName = specialties.find((item) => item.id === selectedSpecialty)?.name || '';
  const selectedDoctor = doctors.find((doctor) => doctor.id === selectedDoctorId);
  const selectedDoctorName = selectedDoctor ? [selectedDoctor.title, selectedDoctor.full_name].filter(Boolean).join(' ') : '';
  const selectedServiceData = services.find((service) => service.id === selectedService);
  const selectedFacilityData = facilities.find((facility) => facility.id === selectedFacility);
  const serviceDuration = selectedServiceData?.duration_minutes ?? null;
  const displaySchedules = schedules;
  const selectedSchedule = displaySchedules.find((schedule) => schedule.id === selectedSlot);
  const scheduleFacility = facilities.find((facility) => facility.id === selectedSchedule?.facility_id) || selectedFacilityData;
  const selectedDisplayEndsAt = selectedSchedule && serviceDuration
    ? new Date(new Date(selectedSchedule.starts_at).getTime() + serviceDuration * 60 * 1000).toISOString()
    : selectedSchedule?.ends_at || '';

  const handleSlotSelection = async (slotId: string) => {
    setBookingError('');
    const previousHold = holdRef.current;
    if (previousHold) {
      holdRef.current = null;
      setHold(null);
      await releaseBookingHold(previousHold.id).catch(() => undefined);
    }
    setSelectedSlot(slotId);
    if (!slotId || !selectedService || !selectedSpecialty) return;

    try {
      const nextHold = await createBookingHold(slotId, selectedService, selectedSpecialty);
      holdRef.current = nextHold;
      setHold(nextHold);
    } catch (error) {
      setSelectedSlot('');
      if (error instanceof BookingApiError && error.status === 409) {
        setBookingError('Khung giờ vừa được giữ bởi người khác. Vui lòng chọn khung giờ khác.');
      } else {
        setBookingError('Không thể giữ khung giờ. Vui lòng thử lại.');
      }
    }
  };

  const handleBooking = async () => {
    if (!selectedDoctorId || !selectedSpecialty || !selectedService || !selectedSlot || !hold) {
      setBookingError('Vui lòng chọn chuyên khoa, dịch vụ, bác sĩ và khung giờ.');
      return;
    }
    if (!reason.trim()) {
      setBookingError('Vui lòng nhập lý do khám trước khi xác nhận.');
      return;
    }
    if (!selectedSchedule || !scheduleFacility) {
      setBookingError('Không xác định được thông tin khung giờ hoặc cơ sở. Vui lòng chọn lại.');
      return;
    }

    setIsBooking(true);
    setBookingError('');
    try {
      const booking = rescheduleId
        ? await rescheduleBooking(rescheduleId, { schedule_id: selectedSlot, hold_id: hold.id })
        : await createBooking({
            hold_id: hold.id,
            schedule_id: selectedSlot,
            doctor_id: selectedDoctorId,
            facility_id: scheduleFacility.id,
            starts_at: selectedSchedule.starts_at,
            ends_at: selectedDisplayEndsAt,
            service_id: selectedService,
            specialty_id: selectedSpecialty,
            encounter_type: selectedType === 'offline' ? 'in_person' : 'telehealth',
            reason: reason.trim(),
            patient_note: patientNote.trim() || undefined,
          }, idempotencyKeyRef.current || (idempotencyKeyRef.current = crypto.randomUUID()));
      bookingCompletedRef.current = true;
      bookingDraft = null;
      navigate(`/patient/appointments/${booking.id}`);
    } catch (error) {
      if (error instanceof BookingApiError && error.status === 409) {
        setBookingError('Khung giờ vừa được đặt hoặc không còn chỗ. Vui lòng chọn khung giờ khác.');
      } else if (error instanceof BookingApiError && error.status === 429) {
        setBookingError('Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.');
      } else if (error instanceof BookingApiError && error.message) {
        setBookingError(error.message);
      } else {
        setBookingError('Không thể đặt lịch lúc này. Vui lòng kiểm tra kết nối và thử lại.');
      }
    } finally {
      setIsBooking(false);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-50 light:bg-app-page p-3 pb-8 text-slate-900 light:text-app-text sm:p-5 sm:pb-8">
      <BookingHeader />

      {(bookingError || catalogError || availabilityError) && (
        <div role="alert" className="mb-5 space-y-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {bookingError && <p>{bookingError}</p>}
          {catalogError && <p>{catalogError}</p>}
          {availabilityError && <p>{availabilityError}</p>}
        </div>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6 xl:grid-cols-[minmax(0,1fr)_350px]">
        <div className="min-w-0 space-y-5">
          <section className="rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-4 shadow-sm sm:p-5">
            <div className="grid gap-6 md:grid-cols-2">
              <SpecialtySelector specialties={specialties} selectedId={selectedSpecialty} onSelect={setSelectedSpecialty} />
              <div className="space-y-5">
                <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
                  Dịch vụ khám
                  <select
                    aria-busy={loadingServices}
                    disabled={loadingServices || !selectedSpecialty}
                    className="mt-2 w-full rounded-xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2.5 font-normal outline-none focus:border-sky-500 light:focus:border-app-primary focus:ring-2 focus:ring-sky-100 disabled:cursor-wait disabled:bg-slate-50 light:disabled:bg-app-page"
                    value={selectedService}
                    onChange={(event) => setSelectedService(event.target.value)}
                  >
                    <option value="">{loadingServices ? 'Đang tải dịch vụ...' : services.length ? 'Chọn dịch vụ' : 'Không có dịch vụ phù hợp'}</option>
                    {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
                  </select>
                </label>
                <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
                  2. Cơ sở khám
                  <select
                    className="mt-2 w-full rounded-xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2.5 font-normal outline-none focus:border-sky-500 light:focus:border-app-primary focus:ring-2 focus:ring-sky-100"
                    value={selectedFacility}
                    onChange={(event) => setSelectedFacility(event.target.value)}
                  >
                    <option value="">Tất cả cơ sở</option>
                    {facilities.map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
                  </select>
                </label>
              </div>
            </div>
          </section>

          <DoctorCard doctors={doctors} selectedDoctorId={selectedDoctorId} onSelectDoctor={setSelectedDoctorId} loading={loadingDoctors} />
          <DateTimeSelector
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
            selectedType={selectedType}
            onSelectType={setSelectedType}
            selectedSlot={selectedSlot}
            onSelectSlot={handleSlotSelection}
            schedules={displaySchedules}
            selectedFacility={scheduleFacility}
            serviceDuration={serviceDuration}
            loading={loadingAvailability}
          />
        </div>

        <div className="min-w-0 lg:sticky lg:top-32" id="booking-confirmation">
          {hold && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Khung giờ đang được giữ trong <strong>{Math.floor(holdSecondsRemaining / 60)}:{String(holdSecondsRemaining % 60).padStart(2, '0')}</strong>.
            </div>
          )}
          <BookingSummary
            patientName={patient?.full_name || 'Chưa cập nhật họ tên'}
            patientPhone={patient?.phone || null}
            specialtyName={selectedSpecialtyName}
            doctorName={selectedDoctorName}
            facilityName={scheduleFacility?.name || ''}
            serviceName={selectedServiceData?.name || ''}
            serviceDuration={selectedServiceData?.duration_minutes ?? null}
            bookingMode={selectedServiceData?.booking_mode ?? null}
            startsAt={selectedSchedule?.starts_at || ''}
            endsAt={selectedDisplayEndsAt}
            type={selectedType}
            price={selectedServiceData?.price ?? null}
            reason={reason}
            patientNote={patientNote}
            onReasonChange={setReason}
            onPatientNoteChange={setPatientNote}
            onBook={handleBooking}
            isBooking={isBooking || rescheduleLoading}
            submitLabel={rescheduleId ? 'Gửi yêu cầu đổi lịch' : undefined}
          />
        </div>
      </div>
    </div>
  );
}
