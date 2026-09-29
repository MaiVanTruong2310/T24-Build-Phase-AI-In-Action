import { memo } from 'react';
import { EmergencyAlertBanner } from './EmergencyAlertBanner';
import { ConsultationReportCard } from './ConsultationReportCard';
import { MatchedDoctorsCard } from './MatchedDoctorsCard';
import { ProposedAppointmentCard } from './ProposedAppointmentCard';
import { RecentVitalsCard } from './RecentVitalsCard';
import { mockConsultationData } from './mockData';

export default memo(function PatientConsultationPage() {
  const data = mockConsultationData;

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Emergency Acute Symptoms Alert Banner */}
      <EmergencyAlertBanner />

      {/* 2. Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Clinical Assessment & Recommended Specialists */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          <ConsultationReportCard data={data} />
          <MatchedDoctorsCard doctors={data.matchedDoctors} />
        </div>

        {/* Right Column: Proposed Appointment & Recent Vitals */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-6">
          <ProposedAppointmentCard appointment={data.proposedAppointment} />
          <RecentVitalsCard vitals={data.vitals} />
        </div>
      </div>
    </div>
  );
});
