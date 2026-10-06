import { memo, useState } from 'react';
import { ShieldCheck, Save } from 'lucide-react';
import type { EmergencyContact } from './types';

interface EmergencyContactFormProps {
  contact: EmergencyContact;
  onSave?: (contact: EmergencyContact) => void;
}

export const EmergencyContactForm = memo(function EmergencyContactForm({
  contact,
  onSave,
}: EmergencyContactFormProps) {
  const [form, setForm] = useState<EmergencyContact>(contact);

  const update = (field: keyof EmergencyContact, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave?.(form);
  };

  return (
    <section className="rounded-xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 dark:border-app-border light:border-app-border px-5 py-4">
        <div className="flex items-start gap-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-950/50 text-amber-500 dark:text-amber-300">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-[15px] font-bold text-slate-800 dark:text-app-text light:text-app-text">
              Chỉnh sửa nhanh thông tin y tế quan trọng
            </h3>
            <p className="mt-0.5 text-[11px] text-slate-400 dark:text-app-secondary light:text-app-secondary">
              Cập nhật thông tin dùng trong các trường hợp cấp cứu, và đồng bộ
              dữ liệu VMedID / GHTT
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-app-secondary light:text-app-secondary">
          <ShieldCheck className="h-3 w-3 text-emerald-500 dark:text-emerald-300" />
          Chuẩn HIPAA & ISO 27001
        </div>
      </div>

      {/* Form body */}
      <div className="px-5 py-4">
        <div className="grid gap-x-5 gap-y-3.5 sm:grid-cols-3">
          {/* Row 1 */}
          <FormField
            label="Họ và tên người liên hệ khẩn cấp"
            value={form.fullName}
            onChange={(v) => update('fullName', v)}
            badge={form.relationship}
          />
          <FormField
            label="Số điện thoại liên hệ khẩn cấp"
            value={form.phone}
            onChange={(v) => update('phone', v)}
          />
          <FormField
            label="Mã Y Tế Bác sĩ Y tế (BSYT)"
            value={form.healthIdCode}
            onChange={(v) => update('healthIdCode', v)}
          />

          {/* Row 2 */}
          <FormField
            label="Tên sử dụng thuốc / thực phẩm"
            value={form.currentMedications}
            onChange={(v) => update('currentMedications', v)}
            isHighlighted
          />
          <div className="sm:col-span-2">
            <FormField
              label="Địa chỉ thường trú đăng ký"
              value={form.address}
              onChange={(v) => update('address', v)}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="mt-5 flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 dark:bg-emerald-700 px-5 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-emerald-700 dark:hover:bg-emerald-700 active:bg-emerald-800 dark:active:bg-emerald-700"
          >
            <Save className="h-3.5 w-3.5" />
            Lưu cập nhật hồ sơ
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface px-4 py-2 text-[13px] font-semibold text-slate-500 dark:text-app-secondary light:text-app-secondary shadow-sm transition hover:bg-slate-50 dark:hover:bg-app-surface light:hover:bg-app-page"
          >
            Huỷ
          </button>
        </div>
      </div>
    </section>
  );
});

/* ─── Reusable form field ───────────────────────────────────────── */
function FormField({
  label,
  value,
  onChange,
  badge,
  isHighlighted,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  badge?: string;
  isHighlighted?: boolean;
}) {
  return (
    <label className="block text-[11px] font-medium text-slate-500 dark:text-app-secondary light:text-app-secondary">
      {label}
      <div className="relative mt-1">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-md border px-2.5 py-2 text-[13px] font-normal transition focus:outline-none focus:ring-1 ${
            isHighlighted
              ? 'border-red-200 dark:border-red-800 bg-red-50/40 dark:bg-red-950/50 text-red-700 dark:text-red-300 focus:border-red-300 dark:focus:border-red-800 focus:ring-red-200 dark:focus:ring-red-400'
              : 'border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface text-slate-700 dark:text-app-text light:text-app-text focus:border-[#0e7490] focus:ring-[#0e7490]/30'
          }`}
        />
        {badge && (
          <span className="absolute right-2 top-1/2 -translate-y-1/2 rounded bg-slate-100 dark:bg-app-muted light:bg-app-muted px-1.5 py-px text-[9px] font-semibold text-slate-500 dark:text-app-secondary light:text-app-secondary">
            {badge}
          </span>
        )}
      </div>
    </label>
  );
}
