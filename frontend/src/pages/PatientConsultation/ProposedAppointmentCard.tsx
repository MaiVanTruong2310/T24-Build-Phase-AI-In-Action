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
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/65 backdrop-blur-md p-5 shadow-xl text-slate-100">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-semibold text-slate-100">
          <Calendar className="h-4 w-4 text-cyan-400" />
          <span>Lịch Khám Đang Đề Xuất</span>
        </h3>
        <span className="rounded-lg border border-blue-500/30 bg-blue-950/40 px-2.5 py-0.5 text-xs font-medium text-cyan-300">
          {appointment.priorityLabel}
        </span>
      </div>

      {/* ─── Doctor Summary ────────────────────────────────────── */}
      <div className="mt-4 flex items-start gap-3.5 rounded-xl border border-slate-800/80 bg-slate-950/60 p-3.5">
        <img
          src={appointment.doctorAvatarUrl}
          alt={appointment.doctorName}
          className="h-12 w-12 rounded-xl object-cover border border-slate-700 shrink-0"
        />
        <div>
          <h4 className="text-sm font-semibold text-slate-100">
            {appointment.doctorName}
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            {appointment.specialty}
          </p>
          <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 text-xs font-medium text-emerald-300">
            <Clock className="h-3 w-3 text-emerald-400" />
            <span>{appointment.timeSlot}</span>
          </div>
        </div>
      </div>

      {/* ─── Appointment Details Table ─────────────────────────── */}
      <div className="mt-4 space-y-2.5 text-xs">
        <div className="flex justify-between items-center py-1.5 border-b border-slate-800/80">
          <span className="text-slate-400">Địa điểm tiếp nhận:</span>
          <span className="font-medium text-slate-200">{appointment.location}</span>
        </div>
        <div className="flex justify-between items-center py-1.5 border-b border-slate-800/80">
          <span className="text-slate-400">Hình thức khám:</span>
          <span className="font-medium text-slate-200">{appointment.serviceType}</span>
        </div>
        <div className="flex justify-between items-center py-1.5">
          <span className="text-slate-400">Chi phí dự kiến:</span>
          <span className="font-semibold text-cyan-400">
            {appointment.fee}{' '}
            <span className="text-[11px] font-normal text-slate-400">
              ({appointment.insuranceNote})
            </span>
          </span>
        </div>
      </div>

      {/* ─── Action Button ─────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setConfirmed(true)}
        disabled={confirmed}
        className={`mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs sm:text-sm font-semibold shadow-md transition active:scale-95 ${
          confirmed
            ? 'bg-emerald-600 text-white cursor-default'
            : 'btn-clinical-primary'
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
            <span>Xác Nhận Giữ Chỗ Ưu Tiên</span>
          </>
        )}
      </button>
    </div>
  );
});
