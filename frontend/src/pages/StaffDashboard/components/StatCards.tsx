import { Link } from 'react-router-dom';
import { CalendarClock, AlertTriangle, MessageSquare, CalendarCheck } from 'lucide-react';
import { KPICardData } from '../types';

interface StatCardsProps {
  kpis: KPICardData[];
}

export function StatCards({ kpis }: StatCardsProps) {
  const getIcon = (id: string) => {
    switch (id) {
      case 'kpi-emergency':
        return <AlertTriangle size={20} className="text-rose-600" />;
      case 'kpi-chat':
        return <MessageSquare size={20} className="text-sky-600" />;
      case 'kpi-confirmed':
        return <CalendarCheck size={20} className="text-emerald-600" />;
      default:
        return <CalendarClock size={20} className="text-sky-600" />;
    }
  };

  const getIconBg = (variant: string) => {
    switch (variant) {
      case 'critical':
        return 'bg-rose-50 border-rose-100';
      case 'warning':
        return 'bg-sky-50 border-sky-100';
      case 'success':
        return 'bg-emerald-50 border-emerald-100';
      default:
        return 'bg-sky-50 border-sky-100';
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
      {kpis.map((kpi) => {
        const isCritical = kpi.variant === 'critical';

        return (
          <div
            key={kpi.id}
            className={`bg-white rounded-2xl border p-4 shadow-2xs flex flex-col justify-between transition-all hover:shadow-xs relative overflow-hidden ${
              isCritical
                ? 'border-rose-300 ring-1 ring-rose-300/60'
                : 'border-slate-200'
            }`}
          >
            {isCritical && (
              <div className="absolute top-0 left-0 w-1.5 h-full bg-rose-600" />
            )}

            <div>
              {/* Header: Title & Icon */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className={`text-xs font-bold ${isCritical ? 'text-rose-700 flex items-center gap-1.5' : 'text-slate-600'}`}>
                  {kpi.title}
                  {isCritical && <span className="w-2 h-2 rounded-full bg-rose-600 animate-ping" />}
                </span>
                <div
                  className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${getIconBg(
                    kpi.variant
                  )}`}
                >
                  {getIcon(kpi.id)}
                </div>
              </div>

              {/* Value & Unit */}
              <div className="flex items-baseline gap-2 mb-4">
                <span
                  className={`text-3xl font-black tracking-tight ${
                    isCritical
                      ? 'text-rose-600'
                      : kpi.variant === 'success'
                      ? 'text-slate-900'
                      : 'text-slate-900'
                  }`}
                >
                  {kpi.value}
                </span>
                <span className="text-xs font-semibold text-slate-500">{kpi.unit}</span>
              </div>
            </div>

            {/* Footer Row */}
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-medium">
              <span
                className={`${
                  isCritical
                    ? 'text-rose-600 font-bold'
                    : kpi.id === 'kpi-appointments'
                    ? 'text-sky-700 bg-sky-50 px-2 py-0.5 rounded-md font-bold text-[11px]'
                    : 'text-slate-500'
                }`}
              >
                {kpi.trendText}
              </span>

              {kpi.actionLink.startsWith('/staff') ? (
                <Link
                  to={kpi.actionLink}
                  className={`font-bold transition-colors ${
                    isCritical
                      ? 'text-rose-700 hover:text-rose-800'
                      : 'text-sky-700 hover:text-sky-800'
                  }`}
                >
                  {kpi.actionText}
                </Link>
              ) : (
                <span className="font-semibold text-slate-600">{kpi.actionText}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
