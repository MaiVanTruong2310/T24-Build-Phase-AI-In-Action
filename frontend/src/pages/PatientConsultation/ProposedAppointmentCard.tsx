import { memo, useState } from 'react';
import { Calendar, Clock, Check, CheckCircle2 } from 'lucide-react';
import type { ProposedAppointment } from './types';

interface Props {
  appointment: ProposedAppointment;
}

export const ProposedAppointmentCard = memo(function ProposedAppointmentCard({
  appointment,
}: Props) {
  const [confirmed, setConfirmed] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-bold text-slate-900">
          <Calendar className="h-4 w-4 text-sky-700" />
          <span>Lịch hẹn đang đề xuất</span>
        </h3>
        <span className="rounded border border-sky-200 bg-sky-50 px-2 py-0.5 text-xs font-semibold text-sky-700">
          {appointment.priorityLabel}
        </span>
      </div>

      {/* ─── Doctor Summary ────────────────────────────────────── */}
      <div className="mt-3.5 flex items-start gap-3 rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5">
        <img
          src={appointment.doctorAvatarUrl}
          alt={appointment.doctorName}
          className="h-12 w-12 rounded-xl object-cover border border-slate-200 shrink-0"
        />
        <div>
          <h4 className="text-sm font-bold text-slate-900">
            {appointment.doctorName}
          </h4>
          <p className="text-xs text-slate-500">
            {appointment.specialty}
          </p>
          <div className="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
            <Clock className="h-3 w-3" />
            <span>{appointment.timeSlot}</span>
          </div>
        </div>
      </div>

      {/* ─── Appointment Details Table ─────────────────────────── */}
      <div className="mt-4 space-y-2.5 text-xs">
        <div className="flex justify-between items-center py-1 border-b border-slate-100">
          <span className="text-slate-500">Địa điểm:</span>
          <span className="font-semibold text-slate-800">{appointment.location}</span>
        </div>
        <div className="flex justify-between items-center py-1 border-b border-slate-100">
          <span className="text-slate-500">Hình thức:</span>
          <span className="font-semibold text-slate-800">{appointment.serviceType}</span>
        </div>
        <div className="flex justify-between items-center py-1">
          <span className="text-slate-500">Phí chuyên khoa:</span>
          <span className="font-bold text-sky-700">
            {appointment.fee}{' '}
            <span className="text-[11px] font-normal text-slate-500">
              {appointment.insuranceNote}
            </span>
          </span>
        </div>
      </div>

      {/* ─── Action Button ─────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setConfirmed(true)}
        disabled={confirmed}
        className={`mt-4 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs sm:text-sm font-bold shadow-sm transition active:scale-95 ${
          confirmed
            ? 'bg-emerald-600 text-white cursor-default'
            : 'bg-sky-700 text-white hover:bg-sky-800'
        }`}
      >
        {confirmed ? (
          <>
            <CheckCircle2 className="h-4 w-4" />
            <span>Đã Giữ Chỗ Khám Thành Công</span>
          </>
        ) : (
          <>
            <Check className="h-4 w-4 stroke-[2.5]" />
            <span>Xác Nhận Giữ Chỗ Khám</span>
          </>
        )}
      </button>
    </div>
  );
});
