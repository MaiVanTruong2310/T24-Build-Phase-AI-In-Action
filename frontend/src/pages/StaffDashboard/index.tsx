import { useState } from 'react';
import { WelcomeHeader } from './components/WelcomeHeader';
import { StatCards } from './components/StatCards';
import { UrgentQueueSection } from './components/UrgentQueueSection';
import { OnDutyDoctorsCard } from './components/OnDutyDoctorsCard';
import { AuditLogCard } from './components/AuditLogCard';
import { DualCheckSafetyCard } from './components/DualCheckSafetyCard';
import { HourlyTrafficChart } from './components/HourlyTrafficChart';
import { FooterBar } from '../ChatTakeover/components/FooterBar';
import {
  MOCK_KPIS,
  MOCK_URGENT_CASES,
  MOCK_ON_DUTY_DOCTORS,
  MOCK_AUDIT_LOGS,
  MOCK_HOURLY_TRAFFIC,
} from './mockData';

export default function StaffDashboard() {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const handleExportReport = () => {
    showToast('Đang kết xuất báo cáo ca trực HITL (PDF/Excel) cho BS. Nguyễn Phương Linh...');
  };

  const handleTriggerAlarm = () => {
    showToast('⚠️ ĐÃ PHÁT TÍN HIỆU BÁO ĐỘNG ĐỎ TOÀN VIỆN: Kích hoạt toàn bộ kíp trực cấp cứu & DSA can thiệp!');
  };

  const handleDispatchStaff = () => {
    showToast('Đang mở bảng điều chuyển nhân lực và phân bổ bác sĩ trực phòng khám...');
  };

  const handleViewAllLogs = () => {
    showToast('Đang truy xuất toàn bộ 142 bản ghi nhật ký can thiệp chuẩn HIPAA...');
  };

  return (
    <div className="min-h-full flex flex-col bg-[#f8fafc] text-slate-800 font-sans p-4 xl:p-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-slate-900 text-white rounded-xl shadow-xl text-xs font-bold flex items-center gap-2 border border-slate-700 animate-bounce">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Welcome Header */}
      <WelcomeHeader
        onExportReport={handleExportReport}
        onTriggerAlarm={handleTriggerAlarm}
      />

      {/* 4 KPI Stat Cards */}
      <StatCards kpis={MOCK_KPIS} />

      {/* Main 2-Column Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-5 items-start">
        {/* Left Column (8 cols): Urgent Queue & Hourly Traffic Chart */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          <UrgentQueueSection urgentCases={MOCK_URGENT_CASES} />
          <HourlyTrafficChart bars={MOCK_HOURLY_TRAFFIC} />
        </div>

        {/* Right Column (4 cols): On-duty Doctors, Audit Logs, Dual-Check Protocol */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          <OnDutyDoctorsCard
            doctors={MOCK_ON_DUTY_DOCTORS}
            onDispatchStaff={handleDispatchStaff}
          />

          <AuditLogCard
            logs={MOCK_AUDIT_LOGS}
            onViewAllLogs={handleViewAllLogs}
          />

          <DualCheckSafetyCard />
        </div>
      </div>

      {/* Bottom Footer Metadata */}
      <FooterBar />
    </div>
  );
}
