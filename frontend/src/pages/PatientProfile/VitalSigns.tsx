import { memo } from 'react';
import { Activity, Eye } from 'lucide-react';
import type { VitalSign } from './types';
import { VitalCard } from './VitalCard';

interface VitalSignsProps {
  vitals: VitalSign[];
  lastUpdated?: string;
}

export const VitalSigns = memo(function VitalSigns({
  vitals,
  lastUpdated = '15/09/2023',
}: VitalSignsProps) {
  return (
    <section>
      {/* Section header */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-[#0e7490] dark:text-emerald-300" />
          <h3 className="text-[15px] font-bold text-slate-800 dark:text-app-text light:text-app-text">
            Chỉ số sinh tồn gần nhất
          </h3>
          <span className="rounded bg-slate-100 dark:bg-app-muted light:bg-app-muted px-2 py-0.5 text-[11px] font-medium text-slate-500 dark:text-app-secondary light:text-app-secondary">
            Cập nhật: {lastUpdated}
          </span>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1 text-[13px] font-semibold text-[#0e7490] dark:text-emerald-300 transition hover:text-[#0c6478] dark:hover:text-emerald-300"
        >
          <Eye className="h-3.5 w-3.5" />
          Xem lịch sử đo ▸
        </button>
      </div>

      {/* Cards grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {vitals.map((vital) => (
          <VitalCard key={vital.id} vital={vital} />
        ))}
      </div>
    </section>
  );
});
