import React, { useState, useEffect } from 'react';

import { BookingHeader, TrustBadges } from '../features/appointment-booking/components/BookingHeader';
import { SpecialtySelector } from '../features/appointment-booking/components/SpecialtySelector';
import { DoctorCard } from '../features/appointment-booking/components/DoctorCard';
import { DateTimeSelector } from '../features/appointment-booking/components/DateTimeSelector';
import { TriageInfo } from '../features/appointment-booking/components/TriageInfo';
import { BookingSummary } from '../features/appointment-booking/components/BookingSummary';
import {
  createBooking,
  fetchSpecialties,
  Specialty,
  fetchDoctors,
  Doctor,
  fetchAvailability,
  Schedule,
  fetchFacilities,
  Facility,
  fetchServices,
  MedicalService,
} from '../features/appointment-booking/api';

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function AppointmentBooking() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState('');
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState('');
  const [services, setServices] = useState<MedicalService[]>([]);
  const [selectedService, setSelectedService] = useState('');

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');

  const [selectedDate, setSelectedDate] = useState(() => formatLocalDate(new Date()));
  const [selectedType, setSelectedType] = useState<'offline' | 'telehealth'>('offline');
  const [selectedSlot, setSelectedSlot] = useState('');
  const [schedules, setSchedules] = useState<Schedule[]>([]);

  const [isBooking, setIsBooking] = useState(false);

  useEffect(() => {
    Promise.all([fetchSpecialties(), fetchFacilities(), fetchServices()])
      .then(([specialtyData, facilityData, serviceData]) => {
        setSpecialties(specialtyData);
        setFacilities(facilityData);
        setServices(serviceData);
        if (specialtyData.length > 0) setSelectedSpecialty(specialtyData[0].id);
        if (facilityData.length > 0) setSelectedFacility(facilityData[0].id);
        if (serviceData.length > 0) setSelectedService(serviceData[0].id);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedSpecialty) return;
    setDoctors([]);
    fetchDoctors({ specialtyId: selectedSpecialty || undefined, facilityId: selectedFacility || undefined })
      .then(data => {
        setDoctors(data);
        if (data.length > 0) {
          setSelectedDoctorId(data[0].id);
        } else {
          setSelectedDoctorId('');
        }
      })
      .catch(console.error);
  }, [selectedSpecialty, selectedFacility]);

  useEffect(() => {
    if (!selectedDoctorId || !selectedDate) return;
    setSchedules([]);
    fetchAvailability(selectedDoctorId, selectedDate, selectedFacility || undefined)
      .then(data => {
        setSchedules(data);
        setSelectedSlot(data[0]?.id || '');
      })
      .catch(console.error);
  }, [selectedDoctorId, selectedDate, selectedFacility]);

  const handleBooking = async () => {
    if (!selectedDoctorId || !selectedSpecialty || !selectedService || !selectedSlot) return;
    setIsBooking(true);
    try {
      await createBooking({
        schedule_id: selectedSlot,
        service_id: selectedService,
        specialty_id: selectedSpecialty,
        encounter_type: selectedType === 'offline' ? 'in_person' : 'telehealth',
        reason: 'Đau thắt ngực nhẹ',
      });
      alert('Đặt lịch thành công!');
    } catch (error) {
      console.error(error);
      alert('Có lỗi xảy ra khi đặt lịch. Vui lòng thử lại.');
    } finally {
      setIsBooking(false);
    }
  };

  const selectedSpecialtyName = specialties.find(s => s.id === selectedSpecialty)?.name || '';
  const selectedDoctor = doctors.find(d => d.id === selectedDoctorId);
  const selectedDoctorName = selectedDoctor ? `${selectedDoctor.title} ${selectedDoctor.full_name}` : '';
  const selectedServiceData = services.find(service => service.id === selectedService);
  const selectedFacilityData = facilities.find(facility => facility.id === selectedFacility);
  const price = selectedServiceData?.price || 0;

  const getSlotTime = (id: string) => {
    const schedule = schedules.find(item => item.id === id);
    return schedule ? new Date(schedule.starts_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '';
  };

  return (
    <div className="bg-slate-50 min-h-screen pb-12">
      <div className="max-w-[1400px] mx-auto px-4 pt-6">

        {/* Header Section */}
        <BookingHeader />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Column 1: Specialty & Doctor */}
          <div className="lg:col-span-3 flex flex-col gap-6">
            <SpecialtySelector
              specialties={specialties}
              selectedId={selectedSpecialty}
              onSelect={setSelectedSpecialty}
            />
            <label className="rounded-xl border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700">
              Cơ sở khám
              <select className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-normal" value={selectedFacility} onChange={(event) => setSelectedFacility(event.target.value)}>
                <option value="">Tất cả cơ sở</option>
                {facilities.map(facility => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
              </select>
            </label>
            <label className="rounded-xl border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700">
              Dịch vụ khám
              <select className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-normal" value={selectedService} onChange={(event) => setSelectedService(event.target.value)}>
                <option value="">Chọn dịch vụ</option>
                {services.map(service => <option key={service.id} value={service.id}>{service.name}</option>)}
              </select>
            </label>
            <DoctorCard
              doctors={doctors}
              selectedDoctorId={selectedDoctorId}
              onSelectDoctor={setSelectedDoctorId}
            />
          </div>

          {/* Column 2: Date & Time */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <DateTimeSelector
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
              selectedType={selectedType}
              onSelectType={setSelectedType}
              selectedSlot={selectedSlot}
              onSelectSlot={setSelectedSlot}
              schedules={schedules.length > 0 ? schedules : undefined}
              selectedFacility={selectedFacilityData}
            />
            <TriageInfo />
          </div>

          {/* Column 3: Summary */}
          <div className="lg:col-span-4">
            <BookingSummary
              specialtyName={selectedSpecialtyName}
              doctorName={selectedDoctorName}
              serviceName={selectedServiceData?.name || ''}
              date={selectedDate}
              slotTime={getSlotTime(selectedSlot)}
              type={selectedType}
              price={price}
              onBook={handleBooking}
              isBooking={isBooking}
            />
          </div>

        </div>

        {/* Footer Badges */}
        <TrustBadges />

      </div>
    </div>
  );
}

