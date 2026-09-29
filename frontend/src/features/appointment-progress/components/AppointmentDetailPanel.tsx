import { CalendarClock, FileText, MapPin, PhoneCall, QrCode, RefreshCw, ShieldCheck, Stethoscope, X } from 'lucide-react';
import { Booking } from '../../appointment-booking/api';
import { AppointmentDisplayData } from '../types';

interface Props {
  booking: Booking | null;
  display: AppointmentDisplayData | null;
  isCancelling: boolean;
  onCancel: () => void;
  onReschedule: () => void;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export function AppointmentDetailPanel({ booking, display, isCancelling, onCancel, onReschedule }: Props) {
  if (!booking || !display) {
    return <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">Chọn một lịch hẹn để xem chi tiết.</div>;
  }

  const canModify = booking.status === 'pending_approval' || booking.status === 'confirmed';
  return (
    <aside className="space-y-5 xl:sticky xl:top-6">
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5">
          <div className="flex items-center justify-between gap-3">
            <div><p className="text-xs font-bold uppercase tracking-wide text-teal-600">Chi tiết lịch hẹn đang chọn</p><h2 className="mt-1 text-xl font-bold text-slate-900">{display.doctorName}</h2><p className="mt-1 text-sm font-semibold text-sky-700">{display.specialtyName} · {display.facilityName}</p></div>
            <div className="rounded-xl bg-sky-50 p-3 text-sky-700"><FileText className="h-5 w-5" /></div>
          </div>
        </div>

        <div className="space-y-5 p-5">
          {booking.status === 'confirmed' ? (
            <div className="rounded-2xl bg-sky-50 p-4">
              <div className="flex items-center gap-3"><QrCode className="h-6 w-6 text-sky-700" /><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Mã check-in</p><p className="mt-1 font-bold text-slate-900">Chưa được cấp</p></div></div>
              <p className="mt-3 text-xs leading-5 text-slate-600">Mã QR/check-in sẽ hiển thị khi cơ sở cung cấp token tiếp đón.</p>
            </div>
          ) : (
            <div className="rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-800"><ShieldCheck className="mr-2 inline h-4 w-4" />Lịch hẹn đang chờ hệ thống và nhân viên điều phối xác nhận.</div>
          )}

          <div className="grid gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4">
            <div className="flex gap-3"><CalendarClock className="mt-0.5 h-5 w-5 text-sky-700" /><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Thời gian</p><p className="mt-1 text-sm font-bold text-slate-900">{formatDateTime(booking.starts_at)}</p><p className="mt-1 text-xs text-slate-500">Kết thúc dự kiến: {new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit' }).format(new Date(booking.ends_at))}</p></div></div>
            <div className="flex gap-3"><MapPin className="mt-0.5 h-5 w-5 text-sky-700" /><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Địa điểm khám</p><p className="mt-1 text-sm font-bold text-slate-900">{display.facilityName}</p></div></div>
            <div className="flex gap-3"><Stethoscope className="mt-0.5 h-5 w-5 text-sky-700" /><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Dịch vụ</p><p className="mt-1 text-sm font-bold text-slate-900">{display.serviceName}</p></div></div>
          </div>

          <div><h3 className="flex items-center gap-2 text-sm font-bold text-slate-900"><FileText className="h-4 w-4 text-sky-700" /> Dặn dò trước khám</h3><div className="mt-3 rounded-2xl border border-dashed border-slate-300 p-4 text-sm leading-6 text-slate-500">Chưa có hướng dẫn trước khám được cung cấp cho lịch hẹn này.</div></div>

          <div className="rounded-2xl bg-slate-50 p-4"><div className="flex items-center gap-3"><PhoneCall className="h-5 w-5 text-sky-700" /><div><p className="text-sm font-bold text-slate-900">Cần hỗ trợ lịch hẹn?</p><p className="text-xs text-slate-500">Liên hệ điều phối viên khi API hỗ trợ được kết nối.</p></div></div></div>

          {canModify && <div className="flex gap-3 border-t border-slate-100 pt-5"><button type="button" onClick={onReschedule} className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-sky-100 px-3 py-3 text-sm font-bold text-sky-700 hover:bg-sky-200"><RefreshCw className="h-4 w-4" /> Đổi lịch hẹn</button><button type="button" onClick={onCancel} disabled={isCancelling} className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 px-3 py-3 text-sm font-bold text-rose-700 hover:bg-rose-50 disabled:cursor-wait disabled:opacity-60"><X className="h-4 w-4" /> {isCancelling ? 'Đang hủy' : 'Hủy lịch'}</button></div>}
        </div>
      </section>
    </aside>
  );
}
