import { memo } from 'react';
import { Edit3, FileDown, AlertTriangle } from 'lucide-react';
import type { Patient, PatientInfoItem } from './types';
import { CreditCard, ShieldCheck, Phone, UserCheck } from 'lucide-react';

interface PatientCardProps {
  patient: Patient;
  infoItems: PatientInfoItem[];
}

const INFO_ICONS = [CreditCard, ShieldCheck, Phone, UserCheck] as const;

/**
 * Combined patient card — merges avatar/badges area AND the info‑bar strip
 * into one single rounded card, matching the screenshot where both sit inside
 * a unified white container with a teal left‑border accent.
 */
export const PatientCard = memo(function PatientCard({
  patient,
  infoItems,
}: PatientCardProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface shadow-sm">
      {/* ─── Top Section: Avatar + Info + Actions ───────────────── */}
      <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-start sm:justify-between">
        {/* Left: Avatar + Text */}
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="relative shrink-0">
            <div className="h-[72px] w-[72px] overflow-hidden rounded-xl bg-gradient-to-br from-slate-200 to-slate-300 shadow-md">
              {patient.avatarUrl ? (
                <img
                  src={patient.avatarUrl}
                  alt={patient.fullName}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-xl font-bold text-white/80">
                  {patient.fullName.charAt(0)}
                </div>
              )}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-500" />
          </div>

          {/* Patient meta */}
          <div className="min-w-0 pt-0.5">
            {/* Name + badges row */}
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold leading-tight text-slate-900 light:text-app-text">
                {patient.fullName}
              </h2>
              <span className="rounded bg-[#0e7490]/10 light:bg-app-primary/10 px-1.5 py-px text-[11px] font-bold text-[#0e7490]">
                {patient.code}
              </span>
              <span className="rounded bg-amber-50 px-1.5 py-px text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200/60">
                {patient.insuranceId}
              </span>
            </div>

            {/* Demographics row */}
            <p className="mt-1.5 flex flex-wrap items-center gap-x-2 text-[13px] text-slate-500 light:text-app-secondary">
              <span>♂ {patient.gender} • {patient.age} tuổi • {patient.dateOfBirth}</span>
              <span className="text-slate-300">|</span>
              <span>Nhóm máu: {patient.bloodType}</span>
            </p>

            {/* Allergy tag */}
            {patient.allergyNote && (
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-red-50 px-2.5 py-1 text-[11px] font-semibold text-red-600 ring-1 ring-inset ring-red-200/60">
                <AlertTriangle className="h-3 w-3" />
                {patient.allergyNote}
              </div>
            )}
          </div>
        </div>

        {/* Right: Action buttons (stacked vertically) */}
        <div className="flex shrink-0 gap-2 sm:flex-col sm:items-end">
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3.5 py-2 text-[13px] font-semibold text-slate-600 light:text-app-secondary shadow-sm transition hover:bg-slate-50 light:hover:bg-app-page active:bg-slate-100 light:active:bg-app-muted"
          >
            <Edit3 className="h-3.5 w-3.5 text-slate-400 light:text-app-secondary" />
            Chỉnh sửa thông tin
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#0e7490] light:bg-app-primary px-3.5 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-[#0c6478] active:bg-[#0a5560]"
          >
            <FileDown className="h-3.5 w-3.5" />
            Xuất PDF / Bác sĩ
          </button>
        </div>
      </div>

      {/* ─── Divider ────────────────────────────────────────────── */}
      <div className="border-t border-slate-100 light:border-app-border" />

      {/* ─── Info Bar Strip (inside the same card) ──────────────── */}
      <div className="grid gap-4 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
        {infoItems.map((item, idx) => {
          const Icon = INFO_ICONS[idx % INFO_ICONS.length];
          return (
            <div key={item.label} className="flex items-start gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 light:bg-app-muted text-slate-500 light:text-app-secondary">
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400 light:text-app-secondary">
                  {item.label}
                </p>
                <p className="mt-px truncate text-[13px] font-semibold text-slate-700 light:text-app-text">
                  {item.value}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
