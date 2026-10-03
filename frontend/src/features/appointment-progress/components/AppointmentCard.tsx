import { CalendarClock, ChevronRight, MapPin, Stethoscope } from 'lucide-react';
import clsx from 'clsx';
import { Booking } from '../../appointment-booking/api';
import { AppointmentDisplayData } from '../types';
import { HITLProgress } from './HITLProgress';

interface Props {
  booking: Booking;
  display: AppointmentDisplayData;
  selected: boolean;
  onSelect: () => void;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function statusLabel(status: Booking['status']): string {
  if (status === 'pending_approval') return 'Đang chờ nhân viên duyệt';
  if (status === 'confirmed') return 'Đã xác nhận';
  if (status === 'rejected') return 'Đã từ chối';
  return 'Đã hủy';
}

function statusStyle(status: Booking['status']): string {
  if (status === 'pending_approval') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (status === 'confirmed') return 'border-teal-200 bg-teal-50 text-teal-700';
  if (status === 'rejected') return 'border-rose-200 bg-rose-50 text-rose-700';
  return 'border-slate-200 bg-slate-100 text-slate-600';
}

export function AppointmentCard({ booking, display, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        'group w-full rounded-3xl border bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md',
        selected ? 'border-sky-300 ring-2 ring-sky-100' : 'border-slate-200',
        booking.status === 'confirmed' && 'border-l-4 border-l-teal-600',
        booking.status === 'pending_approval' && 'border-l-4 border-l-amber-500',
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {display.doctorAvatar ? (
            <img src={display.doctorAvatar} alt={display.doctorName} className="h-12 w-12 rounded-2xl object-cover" />
          ) : (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-sky-700"><Stethoscope className="h-5 w-5" /></div>
          )}
          <div className="min-w-0">
            <span className={clsx('inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold', statusStyle(booking.status))}>{statusLabel(booking.status)}</span>
            <p className="mt-2 truncate text-lg font-bold text-slate-900">{display.doctorName}</p>
            <p className="truncate text-sm font-semibold text-sky-700">{display.specialtyName}</p>
          </div>
        </div>
        <ChevronRight className={clsx('h-5 w-5 shrink-0 text-slate-400 transition group-hover:text-sky-600', selected && 'text-sky-600')} />
      </div>

      <div className="mt-4 grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2">
        <div className="flex items-start gap-2">
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-sky-700" />
          <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Thời gian</p><p className="mt-1 text-sm font-bold text-slate-900">{formatDateTime(booking.starts_at)}</p></div>
        </div>
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-sky-700" />
          <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Cơ sở</p><p className="mt-1 line-clamp-2 text-sm font-bold text-slate-900">{display.facilityName}</p></div>
        </div>
      </div>

      {booking.status === 'pending_approval' && <div className="mt-4"><HITLProgress status={booking.status} /></div>}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
        <span>Mã lịch: #{booking.id.slice(0, 8).toUpperCase()}</span>
        <span className="font-semibold text-sky-700">{display.serviceName}</span>
      </div>
    </button>
  );
}
