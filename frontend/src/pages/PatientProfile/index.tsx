import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { PatientProfileData } from './types';
import { fetchPatientProfile } from './api';
import { Header } from './Header';
import { PatientCard } from './PatientCard';
import { VitalSigns } from './VitalSigns';
import { MedicalTabs } from './MedicalTabs';
import { MedicalTimeline } from './MedicalTimeline';
import { EmergencyContactForm } from './EmergencyContactForm';
import { ProfileFooter } from './Footer';

/**
 * PatientProfile page — full medical record view.
 *
 * Self-contained page with its own Header + Footer.
 * Route: /patient/profile
 */
export default function PatientProfilePage() {
  const [data, setData] = useState<PatientProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('history');

  useEffect(() => {
    fetchPatientProfile('p-001')
      .then(setData)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Không thể tải hồ sơ')
      )
      .finally(() => setLoading(false));
  }, []);

  /* ─── Loading ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex min-h-screen flex-col bg-[#f8fafb]">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-slate-400">
            <Loader2 className="h-7 w-7 animate-spin text-[#0e7490]" />
            <span className="text-[13px] font-medium">
              Đang tải hồ sơ bệnh nhân…
            </span>
          </div>
        </div>
      </div>
    );
  }

  /* ─── Error ───────────────────────────────────────────────────── */
  if (error || !data) {
    return (
      <div className="flex min-h-screen flex-col bg-[#f8fafb]">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-[13px] font-semibold text-red-700">
              {error || 'Không tìm thấy hồ sơ'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  /* ─── Main ────────────────────────────────────────────────────── */
  return (
    <div className="flex min-h-screen flex-col bg-[#f8fafb]">
      <Header />

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-5 px-6 py-6">
        {/* 1. Patient Card (includes info bar strip) */}
        <PatientCard patient={data.patient} infoItems={data.infoBar} />

        {/* 2. Vital Signs grid */}
        <VitalSigns vitals={data.vitalSigns} />

        {/* 3. Medical Tabs */}
        <MedicalTabs
          tabs={data.medicalTabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {/* 4. Medical Timeline */}
        <MedicalTimeline entries={data.timeline} />

        {/* 5. Emergency Contact Form */}
        <EmergencyContactForm
          contact={data.emergencyContact}
          onSave={(updated) =>
            console.log('[PatientProfile] Emergency contact saved:', updated)
          }
        />
      </main>

      <ProfileFooter />
    </div>
  );
}
