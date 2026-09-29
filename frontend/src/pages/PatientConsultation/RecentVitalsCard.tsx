import { memo } from 'react';
import { Activity } from 'lucide-react';
import type { VitalItem } from './types';

interface Props {
  vitals: VitalItem[];
}

export const RecentVitalsCard = memo(function RecentVitalsCard({ vitals }: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-bold text-slate-900">
          <Activity className="h-4 w-4 text-sky-700" />
          <span>Sinh hiệu Gần nhất</span>
        </h3>
        <span className="text-[11px] font-medium text-slate-400">
          Apple Health
        </span>
      </div>

      {/* ─── Grid ──────────────────────────────────────────────── */}
      <div className="mt-3.5 grid grid-cols-2 gap-3">
        {vitals.map((vital) => (
          <div
            key={vital.id}
            className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5"
          >
            <p className="text-[11px] font-medium text-slate-500">
              {vital.label}
            </p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-900">
              {vital.value}{' '}
              {vital.unit && (
                <span className="text-xs font-normal text-slate-500">
                  {vital.unit}
                </span>
              )}
            </p>
            <p
              className={`mt-1 text-[10px] font-semibold ${
                vital.statusType === 'warning'
                  ? 'text-amber-600'
                  : vital.statusType === 'critical'
                  ? 'text-red-600'
                  : 'text-emerald-600'
              }`}
            >
              {vital.status}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
});
