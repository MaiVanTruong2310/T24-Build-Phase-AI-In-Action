import React, { useState } from 'react';

import { BookingHeader, TrustBadges } from '../features/appointment-booking/components/BookingHeader';
import { SpecialtySelector } from '../features/appointment-booking/components/SpecialtySelector';
import { DoctorCard } from '../features/appointment-booking/components/DoctorCard';
import { DateTimeSelector } from '../features/appointment-booking/components/DateTimeSelector';
import { TriageInfo } from '../features/appointment-booking/components/TriageInfo';
import { BookingSummary } from '../features/appointment-booking/components/BookingSummary';

export default function AppointmentBooking() {
  const [selectedSpecialty, setSelectedSpecialty] = useState('tm');
  const [selectedDate, setSelectedDate] = useState('24');
  const [selectedType, setSelectedType] = useState('offline');
  const [selectedSlot, setSelectedSlot] = useState('a2');

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
              selectedId={selectedSpecialty} 
              onSelect={setSelectedSpecialty} 
            />
            <DoctorCard />
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
            <BookingSummary />
          </div>

        </div>

        {/* Footer Badges */}
        <TrustBadges />

      </div>
    </div>
  );
}
