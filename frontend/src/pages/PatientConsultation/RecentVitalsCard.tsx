import { memo } from 'react';
import { Activity } from 'lucide-react';
import type { VitalItem } from './types';

interface Props {
  vitals: VitalItem[];
}

export const RecentVitalsCard = memo(function RecentVitalsCard({ vitals }: Props) {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/65 backdrop-blur-md p-5 shadow-xl text-slate-100">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-semibold text-slate-100">
          <Activity className="h-4 w-4 text-cyan-400" />
          <span>Chỉ Số Sinh Hiệu Mới Nhất</span>
        </h3>
        <span className="text-[11px] font-medium text-slate-400">
          Apple Health Sync
        </span>
      </div>

      {/* ─── Grid ──────────────────────────────────────────────── */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        {vitals.map((vital) => (
          <div
            key={vital.id}
            className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3.5"
          >
            <p className="text-[11px] font-medium text-slate-400">
              {vital.label}
            </p>
            <p className="mt-1 text-xl font-bold tracking-tight text-slate-100 font-mono">
              {vital.value}{' '}
              {vital.unit && (
                <span className="text-xs font-normal text-slate-400">
                  {vital.unit}
                </span>
              )}
            </p>
            <p
              className={`mt-1.5 text-[10px] font-semibold ${
                vital.statusType === 'warning'
                  ? 'text-amber-400'
                  : vital.statusType === 'critical'
                  ? 'text-red-400'
                  : 'text-emerald-400'
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
