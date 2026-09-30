import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { BookingHeader } from '../features/appointment-booking/components/BookingHeader';
import { BookingSummary } from '../features/appointment-booking/components/BookingSummary';
import { DateTimeSelector } from '../features/appointment-booking/components/DateTimeSelector';
import { DoctorCard } from '../features/appointment-booking/components/DoctorCard';
import { SpecialtySelector } from '../features/appointment-booking/components/SpecialtySelector';
import { fetchCurrentUser, PatientProfile } from '../features/patient/api';
import {
  BookingApiError,
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
  MedicalService,
  releaseBookingHold,
  Schedule,
  Specialty,
} from '../features/appointment-booking/api';

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function AppointmentBooking() {
  const navigate = useNavigate();
  const [patient, setPatient] = useState<PatientProfile | null>(null);
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState('');
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState('');
  const [services, setServices] = useState<MedicalService[]>([]);
  const [selectedService, setSelectedService] = useState('');
  const [loadingServices, setLoadingServices] = useState(false);

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [loadingDoctors, setLoadingDoctors] = useState(false);

  const [selectedDate, setSelectedDate] = useState(() => formatLocalDate(new Date()));
  const [selectedType, setSelectedType] = useState<'offline' | 'telehealth'>('offline');
  const [selectedSlot, setSelectedSlot] = useState('');
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loadingAvailability, setLoadingAvailability] = useState(false);

  const [isBooking, setIsBooking] = useState(false);
  const [hold, setHold] = useState<BookingHold | null>(null);
  const [holdSecondsRemaining, setHoldSecondsRemaining] = useState(0);
  const [bookingError, setBookingError] = useState('');
  const [catalogError, setCatalogError] = useState('');
  const [availabilityError, setAvailabilityError] = useState('');
  const [reason, setReason] = useState('');
  const [patientNote, setPatientNote] = useState('');
  const holdRef = useRef<BookingHold | null>(null);
  const idempotencyKeyRef = useRef<string | null>(null);

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

    fetchCurrentUser()
      .then((profile) => {
        if (!cancelled) setPatient(profile);
      })
      .catch(() => {
        // The booking flow can still render; the API remains the source of truth for authentication.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setServices([]);
    setSelectedService('');
    setCatalogError('');

    if (!selectedSpecialty) {
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
        setSelectedService(data[0]?.id || '');
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
  }, [selectedSpecialty, selectedFacility]);

  useEffect(() => {
    let cancelled = false;
    setDoctors([]);
    setSelectedDoctorId('');
    setSchedules([]);
    setSelectedSlot('');
    setAvailabilityError('');

    if (!selectedSpecialty || !selectedService) {
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
        setSelectedDoctorId(data[0]?.id || '');
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
  }, [selectedSpecialty, selectedFacility, selectedService]);

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
      const booking = await createBooking({
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
    <div className="min-h-screen bg-slate-50 pb-12">
      <div className="mx-auto max-w-[1440px] px-4 pt-6 md:px-6">
        <BookingHeader />

        <div className="mb-6 flex justify-end">
          <Link to="/patient/appointments/history" className="rounded-lg border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700 hover:bg-sky-50">
            Xem lịch hẹn của tôi
          </Link>
        </div>

        {(bookingError || catalogError || availabilityError) && (
          <div role="alert" className="mb-6 space-y-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {bookingError && <p>{bookingError}</p>}
            {catalogError && <p>{catalogError}</p>}
            {availabilityError && <p>{availabilityError}</p>}
          </div>
        )}

        <div className="grid items-start gap-6 lg:grid-cols-12">
          <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-3 md:p-6">
            <div className="border-b border-slate-100 pb-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-sky-600">Thông tin tìm kiếm</p>
              <p className="mt-1 text-sm leading-5 text-slate-500">Các lựa chọn sau sẽ quyết định bác sĩ và khung giờ được hiển thị.</p>
            </div>

            <SpecialtySelector specialties={specialties} selectedId={selectedSpecialty} onSelect={setSelectedSpecialty} />

            <label className="block text-sm font-semibold text-slate-700">
              Dịch vụ khám
              <select
                aria-busy={loadingServices}
                disabled={loadingServices || !selectedSpecialty}
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:cursor-wait disabled:bg-slate-50"
                value={selectedService}
                onChange={(event) => setSelectedService(event.target.value)}
              >
                <option value="">{loadingServices ? 'Đang tải dịch vụ...' : services.length ? 'Chọn dịch vụ' : 'Không có dịch vụ phù hợp'}</option>
                {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
              </select>
            </label>

          </section>

          <main className="lg:col-span-5">
            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
              <label className="block text-sm font-semibold text-slate-700">
                2. Cơ sở khám
                <select className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100" value={selectedFacility} onChange={(event) => setSelectedFacility(event.target.value)}>
                  <option value="">Tất cả cơ sở</option>
                  {facilities.map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
                </select>
              </label>
            </div>
            <div className="mb-6">
              <DoctorCard doctors={doctors} selectedDoctorId={selectedDoctorId} onSelectDoctor={setSelectedDoctorId} loading={loadingDoctors} />
            </div>
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
          </main>

          <div className="lg:col-span-4">
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
              isBooking={isBooking}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
