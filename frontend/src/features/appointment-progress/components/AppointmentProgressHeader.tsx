import { CalendarPlus } from 'lucide-react';
import { Link } from 'react-router-dom';

export function AppointmentProgressHeader() {
  return (
    <header className="ap-head">
      <div>
        <p className="ap-kicker">Hồ sơ theo dõi</p>
        <h1 className="ap-title">Tiến trình điều trị & Lịch hẹn</h1>
        <p className="ap-sub">Theo dõi trạng thái các lượt khám bác sĩ, gói khám sức khỏe và điều phối AI.</p>
      </div>
      <Link to="/patient/appointments" className="ap-btn ap-btn--primary">
        <CalendarPlus size={18} aria-hidden="true" /> Đặt lịch mới
      </Link>
    </header>
  );
}

export function HitlTrustBadge() {
  return null;
}
