import { memo, useMemo } from 'react';
import type { VitalSign } from './types';

interface VitalCardProps {
  vital: VitalSign;
}

/* ─── Tiny sparkline SVG (area-fill) ────────────────────────────── */
function Sparkline({
  data,
  strokeColor,
  fillColor,
}: {
  data: number[];
  strokeColor: string;
  fillColor: string;
}) {
  const width = 80;
  const height = 36;
  const padding = 2;

  const { line, area } = useMemo(() => {
    if (data.length < 2) return { line: '', area: '' };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pts = data.map((v, i) => {
      const x = padding + (i / (data.length - 1)) * (width - padding * 2);
      const y =
        height - padding - ((v - min) / range) * (height - padding * 2 - 4);
      return { x, y };
    });
    const line = pts.map((p) => `${p.x},${p.y}`).join(' ');
    const last = pts[pts.length - 1];
    const first = pts[0];
    const area = `${line} ${last.x},${height} ${first.x},${height}`;
    return { line, area };
  }, [data]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-9 w-full"
      preserveAspectRatio="none"
    >
      <polygon points={area} fill={fillColor} />
      <polyline
        points={line}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ─── Status badge styles ───────────────────────────────────────── */
const STATUS_STYLES: Record<
  string,
  { badge: string; sparkStroke: string; sparkFill: string }
> = {
  normal: {
    badge: 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-300 ring-1 ring-inset ring-emerald-200/60 dark:ring-emerald-400/60',
    sparkStroke: '#10b981',
    sparkFill: 'rgba(16,185,129,0.08)',
  },
  warning: {
    badge: 'bg-amber-50 dark:bg-amber-950/50 text-amber-600 dark:text-amber-300 ring-1 ring-inset ring-amber-200/60 dark:ring-amber-400/60',
    sparkStroke: '#f59e0b',
    sparkFill: 'rgba(245,158,11,0.08)',
  },
  critical: {
    badge: 'bg-red-50 dark:bg-red-950/50 text-red-600 dark:text-red-300 ring-1 ring-inset ring-red-200/60 dark:ring-red-400/60',
    sparkStroke: '#ef4444',
    sparkFill: 'rgba(239,68,68,0.08)',
  },
};

/* ─── Per-icon accent ───────────────────────────────────────────── */
const ICON_STYLES: Record<string, { bg: string; emoji: string }> = {
  'heart-pulse': { bg: 'bg-teal-50 dark:bg-teal-950/50', emoji: '🫀' },
  activity: { bg: 'bg-rose-50 dark:bg-rose-950/50', emoji: '❤️' },
  scale: { bg: 'bg-cyan-50 dark:bg-cyan-950/50 light:bg-app-muted', emoji: '⚖️' },
  droplets: { bg: 'bg-violet-50 dark:bg-violet-950/50', emoji: '🩸' },
};

export const VitalCard = memo(function VitalCard({ vital }: VitalCardProps) {
  const sts = STATUS_STYLES[vital.status];
  const icon = ICON_STYLES[vital.icon] ?? { bg: 'bg-slate-50 dark:bg-app-surface light:bg-app-page', emoji: '💊' };

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface shadow-sm transition hover:shadow-md">
      {/* Card body */}
      <div className="flex flex-1 flex-col px-4 pt-4 pb-2">
        {/* Top row: icon + status */}
        <div className="flex items-start justify-between">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-lg text-base ${icon.bg}`}
          >
            {icon.emoji}
          </div>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${sts.badge}`}>
            {vital.statusLabel}
          </span>
        </div>

        {/* Label */}
        <p className="mt-2.5 text-[11px] font-medium uppercase tracking-wider text-slate-400 dark:text-app-secondary light:text-app-secondary">
          {vital.label}
        </p>

        {/* Value */}
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className="text-[28px] font-extrabold leading-none tracking-tight text-slate-900 dark:text-app-text light:text-app-text">
            {vital.value}
          </span>
          <span className="text-[13px] font-medium text-slate-400 dark:text-app-secondary light:text-app-secondary">
            {vital.unit}
          </span>
        </div>

        {/* Sub-label */}
        <p className="mt-1 text-[11px] text-slate-400 dark:text-app-secondary light:text-app-secondary">
          {vital.referenceRange}
        </p>
      </div>

      {/* Sparkline – sits flush at card bottom */}
      <div className="mt-auto">
        <Sparkline
          data={vital.trendData}
          strokeColor={sts.sparkStroke}
          fillColor={sts.sparkFill}
        />
      </div>
    </div>
  );
});
