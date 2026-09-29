import {
  ChevronRight, Clock, ShieldCheck, Brain,
  CheckCircle2, XCircle, Calendar, Stethoscope, Loader2,
  Building2, Video, ChevronDown,
} from 'lucide-react';
import type { PendingBooking } from '../api';
import { STATUS_CONFIG, RISK_CONFIG, formatTime, formatDate, formatRelative } from './constants';

interface BookingCardProps {
  booking: PendingBooking;
  isExpanded: boolean;
  onToggle: () => void;
  onOpenDetail: () => void;
  onApprove: () => void;
  onReject: () => void;
  isActioning: boolean;
}

export function BookingCard({ booking, isExpanded, onToggle, onOpenDetail, onApprove, onReject, isActioning }: BookingCardProps) {
  const status = STATUS_CONFIG[booking.status];
  const risk = booking.triage ? RISK_CONFIG[booking.triage.risk_level] : null;
  const RiskIcon = risk?.icon ?? ShieldCheck;
  const isPending = booking.status === 'pending_approval';

  return (
    <div
      className={`bg-white border rounded-2xl transition-all duration-200 hover:shadow-md group ${
        isPending
          ? 'border-amber-200 hover:border-amber-300 shadow-sm'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {/* Main row */}
      <div className="px-5 py-4 flex items-center gap-4">
        {/* Status dot + avatar */}
        <div className="relative flex-shrink-0">
          <img
            src={booking.doctor_avatar || `https://i.pravatar.cc/150?u=${booking.id}`}
            alt={booking.doctor_name}
            className="w-12 h-12 rounded-xl object-cover border border-slate-200"
          />
          <div
            className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-white ${status.dot}`}
            title={status.label}
          />
        </div>

        {/* Info block */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-bold text-slate-900 text-sm truncate">{booking.patient_name}</span>
            <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
              {booking.booking_code}
            </span>
            {risk && (
              <span className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${risk.bg} ${risk.text}`}>
                <RiskIcon size={10} />
                {risk.label}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-500 flex-wrap">
            <span className="flex items-center gap-1">
              <Stethoscope size={12} className="text-sky-500" />
              {booking.specialty_name}
            </span>
            <span className="hidden sm:inline text-slate-300">•</span>
            <span className="hidden sm:flex items-center gap-1">
              <Calendar size={12} />
              {formatDate(booking.starts_at)}
            </span>
            <span className="flex items-center gap-1 font-semibold text-slate-700">
              <Clock size={12} className="text-sky-500" />
              {formatTime(booking.starts_at)}
            </span>
          </div>

          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 flex-wrap">
            <span className="flex items-center gap-1">
              {booking.encounter_type === 'telehealth' ? (
                <><Video size={12} className="text-indigo-400" /> Telehealth</>
              ) : (
                <><Building2 size={12} /> {booking.facility_name}</>
              )}
            </span>
            <span className="hidden sm:inline text-slate-300">•</span>
            <span className="hidden sm:inline">{booking.doctor_name}</span>
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${status.bg} ${status.text} border ${status.border}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>

          {booking.triage && (
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold border border-indigo-100">
              <Brain size={12} />
              AI {booking.triage.confidence}%
            </div>
          )}

          <span className="hidden xl:inline text-[11px] text-slate-400 font-medium w-20 text-right">
            {formatRelative(booking.requested_at)}
          </span>

          <button
            onClick={onToggle}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ChevronDown size={16} className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </button>

          {isPending && (
            <button
              onClick={onOpenDetail}
              className="flex items-center gap-1.5 px-4 py-2 bg-sky-600 text-white text-sm font-bold rounded-xl hover:bg-sky-700 transition-colors shadow-sm shadow-sky-200"
            >
              Thẩm định
              <ChevronRight size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Expanded detail panel */}
      {isExpanded && (
        <ExpandedPanel
          booking={booking}
          isPending={isPending}
          onOpenDetail={onOpenDetail}
          onApprove={onApprove}
          onReject={onReject}
          isActioning={isActioning}
        />
      )}
    </div>
  );
}

/* ─── Expanded panel sub-component ─── */

function ExpandedPanel({
  booking,
  isPending,
  onOpenDetail,
  onApprove,
  onReject,
  isActioning,
}: {
  booking: PendingBooking;
  isPending: boolean;
  onOpenDetail: () => void;
  onApprove: () => void;
  onReject: () => void;
  isActioning: boolean;
}) {
  return (
    <div className="border-t border-slate-100 px-5 py-4 bg-slate-50/60 animate-in fade-in slide-in-from-top-1 duration-200">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Patient info */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Thông tin bệnh nhân</p>
          <p className="text-sm font-bold text-slate-900">{booking.patient_name}</p>
          <p className="text-xs text-slate-500 mt-1">
            {booking.patient_age} tuổi • {booking.patient_gender === 'male' ? 'Nam' : 'Nữ'}
          </p>
          <p className="text-xs text-slate-500 mt-1">CCCD: {booking.patient_cccd}</p>
          <p className="text-xs text-slate-500 mt-0.5">BHYT: {booking.patient_bhyt}</p>
        </div>

        {/* Reason + note */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Lý do khám</p>
          <p className="text-sm text-slate-700 leading-relaxed">{booking.reason}</p>
          {booking.patient_note && (
            <p className="text-xs text-slate-500 italic mt-2 pl-3 border-l-2 border-slate-200">
              "{booking.patient_note}"
            </p>
          )}
        </div>

        {/* AI Triage */}
        {booking.triage && (
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Brain size={12} className="text-indigo-500" />
              AI Triage
            </p>
            <p className="text-sm font-semibold text-indigo-700">{booking.triage.specialty_match}</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-teal-500 rounded-full transition-all"
                  style={{ width: `${booking.triage.confidence}%` }}
                />
              </div>
              <span className="text-xs font-bold text-slate-600">{booking.triage.confidence}%</span>
            </div>
            {booking.triage.suggested_preclinical.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {booking.triage.suggested_preclinical.map(item => (
                  <span key={item} className="text-[10px] font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                    {item}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-end gap-3 mt-4">
        {isPending && (
          <>
            <button onClick={onReject} disabled={isActioning} className="flex items-center gap-1.5 px-4 py-2 border-2 border-rose-100 text-rose-600 font-bold text-sm rounded-xl hover:bg-rose-50 transition-colors disabled:opacity-50">
              {isActioning ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
              Từ chối
            </button>
            <button onClick={onApprove} disabled={isActioning} className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white font-bold text-sm rounded-xl hover:bg-teal-700 transition-colors shadow-sm disabled:opacity-50">
              {isActioning ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
              Phê duyệt ngay
            </button>
          </>
        )}
        <button
          onClick={onOpenDetail}
          className="flex items-center gap-1.5 px-4 py-2 border border-slate-200 text-slate-700 font-bold text-sm rounded-xl hover:bg-slate-50 transition-colors"
        >
          Xem chi tiết đầy đủ
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
