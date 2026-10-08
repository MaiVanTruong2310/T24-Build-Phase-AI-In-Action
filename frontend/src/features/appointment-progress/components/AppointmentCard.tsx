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

function statusStyle(status: Booking['status']): string {
  if (status === 'pending_approval') return 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300';
  if (status === 'confirmed') return 'border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/50 text-teal-800 dark:text-teal-300';
  if (status === 'rejected') return 'border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300';
  return 'border-slate-200 dark:border-app-border bg-slate-100 dark:bg-app-muted text-slate-600 dark:text-app-secondary';
}

interface Props {
  booking: Booking;
  display: AppointmentDisplayData;
  onSelect: () => void;
}

export function AppointmentCard({ booking, display, onSelect }: Props) {
  const isPackage = display.bookingType === 'package';
  const isCoord = display.bookingType === 'coordination';

  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        'group w-full rounded-2xl border bg-white dark:bg-app-surface light:bg-app-surface p-5 text-left shadow-2xs transition hover:-translate-y-0.5 hover:shadow-md cursor-pointer border-slate-200 dark:border-app-border light:border-app-border',
        booking.status === 'confirmed' && 'border-l-4 border-l-teal-600',
        booking.status === 'pending_approval' && (isPackage ? 'border-l-4 border-l-emerald-500' : isCoord ? 'border-l-4 border-l-indigo-500' : 'border-l-4 border-l-amber-500'),
        booking.status === 'cancelled' && 'border-l-4 border-l-slate-400 opacity-80',
      )}
    >
      {/* Phân loại & Trạng thái */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-app-border light:border-app-border pb-3 mb-3.5">
        <span className={clsx('inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-bold shadow-2xs', display.typeBadge.bg, display.typeBadge.text, display.typeBadge.border)}>
          <span>{display.typeBadge.icon}</span>
          <span>{display.typeBadge.label}</span>
        </span>
        <span className={clsx('inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-bold', statusStyle(booking.status))}>
          {statusLabel(booking.status, display.bookingType)}
        </span>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {display.doctorAvatar ? (
            <img src={display.doctorAvatar} alt={display.primaryTitle} className="h-12 w-12 rounded-xl object-cover shrink-0" />
          ) : isPackage ? (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
              <Package className="h-6 w-6" />
            </div>
          ) : isCoord ? (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              <UserRoundCheck className="h-6 w-6" />
            </div>
          ) : (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-sky-100 dark:bg-sky-950/50 light:bg-app-tint text-sky-700 dark:text-sky-300 light:text-app-primary border border-sky-200 dark:border-sky-800">
              <Stethoscope className="h-6 w-6" />
            </div>
          )}
          <div className="min-w-0">
            <p className="line-clamp-1 text-base font-bold text-slate-900 dark:text-app-text light:text-app-text group-hover:text-emerald-700 dark:group-hover:text-emerald-400 transition-colors">
              {display.primaryTitle}
            </p>
            <p className="mt-0.5 truncate text-xs font-semibold text-slate-600 dark:text-app-secondary light:text-app-secondary">
              {display.secondaryTitle}
            </p>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 shrink-0 text-slate-400 dark:text-app-secondary transition group-hover:translate-x-1 group-hover:text-emerald-600" />
      </div>

      <div className="mt-3.5 grid gap-2.5 rounded-xl bg-slate-50 dark:bg-app-surface light:bg-app-page p-3 sm:grid-cols-2 text-xs">
        <div className="flex items-start gap-2">
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-slate-600 dark:text-app-secondary" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">
              {isPackage ? 'Ngày & Buổi khám' : 'Thời gian hẹn'}
            </p>
            <p className="mt-0.5 text-xs font-bold text-slate-900 dark:text-app-text">
              {display.startsAtFormatted}
            </p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-slate-600 dark:text-app-secondary" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary">Cơ sở</p>
            <p className="mt-0.5 line-clamp-1 text-xs font-bold text-slate-900 dark:text-app-text">{display.facilityName}</p>
          </div>
        </div>
      </div>

      {booking.status === 'pending_approval' && (
        <div className="mt-3.5">
          <HITLProgress status={booking.status} progress={display.progress} />
        </div>
      )}

      <div className="mt-3.5 flex items-center justify-between text-xs text-slate-500 dark:text-app-secondary border-t border-slate-100 dark:border-app-border pt-2.5">
        <span className="font-mono text-[11px]">#{booking.id ? booking.id.slice(0, 8).toUpperCase() : ''}</span>
        <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-400 group-hover:underline">
          Xem chi tiết <ChevronRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </button>
  );
}


