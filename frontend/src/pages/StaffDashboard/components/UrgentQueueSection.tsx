import { Link } from 'react-router-dom';
import { ShieldAlert, HeartPulse, Bell, Bot, Clock, CalendarDays } from 'lucide-react';
import { UrgentCaseItem } from '../types';

interface UrgentQueueSectionProps {
  urgentCases: UrgentCaseItem[];
}

export function UrgentQueueSection({ urgentCases }: UrgentQueueSectionProps) {
  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'critical':
        return 'bg-rose-600 text-white font-black';
      case 'clinical_warning':
        return 'bg-sky-100 text-sky-800 font-bold border border-sky-200';
      case 'low_confidence':
        return 'bg-indigo-100 text-indigo-800 font-bold border border-indigo-200';
      case 'reschedule':
        return 'bg-teal-100 text-teal-800 font-bold border border-teal-200';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  const getCaseIcon = (type: string) => {
    switch (type) {
      case 'critical':
        return <HeartPulse size={16} className="text-rose-600 shrink-0 mt-0.5" />;
      case 'clinical_warning':
        return <Bell size={16} className="text-amber-600 shrink-0 mt-0.5" />;
      case 'low_confidence':
        return <Bot size={16} className="text-sky-600 shrink-0 mt-0.5" />;
      case 'reschedule':
        return <Clock size={16} className="text-teal-600 shrink-0 mt-0.5" />;
      default:
        return <ShieldAlert size={16} className="text-slate-500 shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-pulse"></span>
          <h2 className="text-base font-extrabold text-slate-900">
            Yêu cầu khẩn & HITL Queue cần can thiệp ngay
          </h2>
        </div>
        <span className="text-xs font-bold text-slate-500 tracking-wide uppercase">
          {urgentCases.length} CA ƯU TIÊN CAO NHẤT
        </span>
      </div>

      {/* List of 4 Urgent Cases */}
      <div className="space-y-3">
        {urgentCases.map((item) => {
          const isCritical = item.priorityType === 'critical';

          return (
            <div
              key={item.id}
              className={`p-4 rounded-2xl border transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                isCritical
                  ? 'bg-rose-50/50 border-rose-200 shadow-2xs'
                  : 'bg-slate-50/60 border-slate-200/80 hover:bg-slate-50 hover:border-slate-300'
              }`}
            >
              <div className="flex items-start gap-3.5 min-w-0">
                {/* Avatar */}
                <div className="relative shrink-0">
                  {item.avatar ? (
                    <img
                      src={item.avatar}
                      alt={item.patientName}
                      className="w-11 h-11 rounded-full object-cover border-2 border-white shadow-2xs"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-full bg-slate-200 text-slate-700 font-bold flex items-center justify-center">
                      {item.patientName.charAt(0)}
                    </div>
                  )}
                  {isCritical && (
                    <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-rose-600 rounded-full border-2 border-white flex items-center justify-center text-[9px] font-black text-white">
                      !
                    </span>
                  )}
                </div>

                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-black text-slate-900 leading-tight">
                      {item.patientName}
                    </h3>
                    <span className="text-xs font-semibold text-slate-500">
                      {item.age} tuổi • {item.gender}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-md uppercase tracking-wider ${getBadgeStyle(
                        item.priorityType
                      )}`}
                    >
                      {item.priorityBadge}
                    </span>
                  </div>

                  {/* Alert Description */}
                  <div className="flex items-start gap-1.5">
                    {getCaseIcon(item.priorityType)}
                    <p
                      className={`text-xs leading-relaxed ${
                        isCritical
                          ? 'text-rose-700 font-extrabold'
                          : 'text-slate-800 font-bold'
                      }`}
                    >
                      {item.alertText}
                    </p>
                  </div>

                  {/* Meta source */}
                  <p className="text-[11px] text-slate-500 font-medium pl-5">
                    {item.sourceText}
                  </p>
                </div>
              </div>

              {/* Action Button */}
              <div className="shrink-0 self-end md:self-center">
                <Link
                  to={item.actionLink}
                  className={`inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                    isCritical
                      ? 'bg-rose-700 hover:bg-rose-800 text-white'
                      : item.actionType === 'takeover'
                      ? 'bg-sky-700 hover:bg-sky-800 text-white'
                      : 'bg-white hover:bg-slate-100 text-slate-800 border border-slate-300'
                  }`}
                >
                  {isCritical && <ShieldAlert size={14} />}
                  {item.actionType === 'takeover' && <Bot size={14} />}
                  {item.actionType === 'reschedule' && <CalendarDays size={14} />}
                  <span>{item.actionLabel}</span>
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
