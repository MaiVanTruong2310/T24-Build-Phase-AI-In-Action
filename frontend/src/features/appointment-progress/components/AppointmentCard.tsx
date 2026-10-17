import { CalendarClock, ChevronRight, MapPin, Package, Stethoscope, UserRoundCheck } from 'lucide-react';
import clsx from 'clsx';
import { Booking } from '../../appointment-booking/api';
import { AppointmentDisplayData } from '../types';
import { HITLProgress } from './HITLProgress';

function statusLabel(status: Booking['status'], type: AppointmentDisplayData['bookingType']): string {
  if (status === 'pending_approval') {
    if (type === 'package') return 'Chờ tư vấn gói';
    if (type === 'coordination') return 'Đang phân luồng';
    return 'Chờ xác nhận';
  }
  if (status === 'confirmed') return 'Đã xác nhận';
  if (status === 'rejected') return 'Đã từ chối';
  if (status === 'expired') return 'Đã hết hạn';
  return 'Đã hủy';
}

interface Props {
  booking: Booking;
  display: AppointmentDisplayData;
  onSelect: () => void;
}

export function AppointmentCard({ booking, display, onSelect }: Props) {
  const isPackage = display.bookingType === 'package';
  const isCoord = display.bookingType === 'coordination';
  const Icon = isPackage ? Package : isCoord ? UserRoundCheck : Stethoscope;

  return (
    <button type="button" onClick={onSelect} className={clsx('ap-card', `ap-card--${booking.status}`)}>
      <div className="ap-card__top">
        <span className="ap-type"><span aria-hidden="true">{display.typeBadge.icon}</span>{display.typeBadge.label}</span>
        <span className={clsx('ap-status', `ap-status--${booking.status}`)}>{statusLabel(booking.status, display.bookingType)}</span>
      </div>

      <div className="ap-who">
        <span className="ap-avatar">
          {display.doctorAvatar ? <img src={display.doctorAvatar} alt="" referrerPolicy="no-referrer" /> : <Icon size={24} aria-hidden="true" />}
        </span>
        <span className="ap-who__text">
          <p className="ap-who__title">{display.primaryTitle}</p>
          <p className="ap-who__sub">{display.secondaryTitle}</p>
        </span>
        <ChevronRight className="ap-go" size={20} aria-hidden="true" />
      </div>

      <dl className="ap-facts">
        <div className="ap-fact">
          <CalendarClock size={16} aria-hidden="true" />
          <div><dt>{isPackage ? 'Ngày & buổi khám' : 'Thời gian hẹn'}</dt><dd>{display.startsAtFormatted}</dd></div>
        </div>
        <div className="ap-fact">
          <MapPin size={16} aria-hidden="true" />
          <div><dt>Cơ sở</dt><dd>{display.facilityName}</dd></div>
        </div>
      </dl>

      {booking.status === 'pending_approval' && <HITLProgress status={booking.status} progress={display.progress} />}

      <div className="ap-card__foot">
        <span className="ap-code">#{booking.id ? booking.id.slice(0, 8).toUpperCase() : ''}</span>
        <span className="ap-more">Xem chi tiết</span>
      </div>
    </button>
  );
}
