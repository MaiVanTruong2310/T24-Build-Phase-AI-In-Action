import React, { useState, useEffect } from 'react';

import { BookingHeader, TrustBadges } from '../features/appointment-booking/components/BookingHeader';
import { SpecialtySelector } from '../features/appointment-booking/components/SpecialtySelector';
import { DoctorCard } from '../features/appointment-booking/components/DoctorCard';
import { DateTimeSelector } from '../features/appointment-booking/components/DateTimeSelector';
import { TriageInfo } from '../features/appointment-booking/components/TriageInfo';
import { BookingSummary } from '../features/appointment-booking/components/BookingSummary';
import { fetchSpecialties, Specialty, fetchDoctors, Doctor, createBooking } from '../features/appointment-booking/api';

export default function AppointmentBooking() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState('');

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');

  const [selectedDate, setSelectedDate] = useState('24');
  const [selectedType, setSelectedType] = useState<'offline' | 'telehealth'>('offline');
  const [selectedSlot, setSelectedSlot] = useState('a2');

  const [isBooking, setIsBooking] = useState(false);

  useEffect(() => {
    fetchSpecialties()
      .then(data => {
        setSpecialties(data);
        if (data.length > 0) setSelectedSpecialty(data[0].id);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedSpecialty) return;
    setDoctors([]);
    fetchDoctors(selectedSpecialty)
      .then(data => {
        setDoctors(data);
        if (data.length > 0) {
          setSelectedDoctorId(data[0].id);
        } else {
          setSelectedDoctorId('');
        }
      })
      .catch(console.error);
  }, [selectedSpecialty]);

  const handleBooking = async () => {
    if (!selectedDoctorId || !selectedSpecialty || !selectedSlot) return;

    setIsBooking(true);
    try {
      await createBooking({
        schedule_id: selectedSlot,
        service_id: 'srv_123',
        specialty_id: selectedSpecialty,
        ai_triage_id: 'tri_456',
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
  const price = selectedDoctor?.price || 350000;

  const getSlotTime = (id: string) => {
    const slots: Record<string, string> = {
      m1: '08:00', m2: '08:45', m3: '09:30', m4: '10:15',
      a1: '13:30', a2: '14:15', a3: '15:00', a4: '16:00'
    };
    return slots[id] || '';
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
            />
            <TriageInfo />
          </div>

          {/* Column 3: Summary */}
          <div className="lg:col-span-4">
            <BookingSummary
              specialtyName={selectedSpecialtyName}
              doctorName={selectedDoctorName}
              date={`${selectedDate}/10/2023`}
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
