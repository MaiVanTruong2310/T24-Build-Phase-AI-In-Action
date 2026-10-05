import { TypewriterLoader } from '../../../components/TypewriterLoader';
import { CalendarDays, FileText, ShieldCheck } from 'lucide-react';

interface Props {
  patientName: string;
  patientPhone: string | null;
  specialtyName: string;
  doctorName: string;
  facilityName: string;
  serviceName: string;
  serviceDuration: number | null;
  bookingMode: 'group' | 'doctor_visit' | null;
  startsAt: string;
  endsAt: string;
  type: 'offline' | 'telehealth';
  price: number | null;
  reason: string;
  patientNote: string;
  onReasonChange: (value: string) => void;
  onPatientNoteChange: (value: string) => void;
  onBook: () => void;
  isBooking: boolean;
  submitLabel?: string;
}

function formatDateTime(value: string): string {
  if (!value) return 'Chưa chọn';
  return new Intl.DateTimeFormat('vi-VN', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatPrice(value: number | null): string {
  if (value === null || Number.isNaN(value)) return 'Chưa cập nhật';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts.slice(-2).map((part) => part[0]).join('').toUpperCase() || 'BN';
}

export function BookingSummary({
  patientName,
  patientPhone,
  specialtyName,
  doctorName,
  facilityName,
  serviceName,
  serviceDuration,
  bookingMode,
  startsAt,
  endsAt,
  type,
  price,
  reason,
  patientNote,
  onReasonChange,
  onPatientNoteChange,
  onBook,
  isBooking,
  submitLabel = 'Xác nhận đặt lịch',
}: Props) {
  return (
    <aside className="space-y-5">
      <div className="overflow-hidden rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface shadow-sm">
        <div className="border-b border-slate-100 light:border-app-border bg-slate-50 light:bg-app-page p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-600 light:text-app-primary">Bước 5</p>
          <h2 className="mt-1 flex items-center gap-2 text-lg font-bold text-slate-900 light:text-app-text">
            <FileText className="h-5 w-5 text-sky-600 light:text-app-primary" /> Kiểm tra thông tin
          </h2>
        </div>

        <div className="p-5">
          <div className="flex items-center gap-3 border-b border-slate-100 light:border-app-border pb-5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-sky-100 light:bg-app-tint font-bold text-sky-700 light:text-app-primary">{initials(patientName)}</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-slate-900 light:text-app-text">{patientName || 'Chưa cập nhật họ tên'}</p>
              {patientPhone && <p className="mt-1 text-xs text-slate-500 light:text-app-secondary">{patientPhone}</p>}
            </div>
          </div>

          <dl className="mt-5 space-y-3 text-sm">
            <SummaryRow label="Chuyên khoa" value={specialtyName} />
            <SummaryRow label="Dịch vụ" value={serviceName} />
            {serviceDuration !== null && <SummaryRow label="Thời lượng" value={`${serviceDuration} phút`} />}
            <SummaryRow label="Bác sĩ" value={doctorName} accent />
            <SummaryRow label="Cơ sở" value={facilityName} />
            <SummaryRow label="Thời gian" value={startsAt ? `${formatDateTime(startsAt)}${endsAt ? ` – ${formatDateTime(endsAt)}` : ''}` : ''} />
            <SummaryRow label="Hình thức" value={type === 'offline' ? 'Khám tại cơ sở' : 'Khám trực tuyến'} />
            {bookingMode && <SummaryRow label="Loại dịch vụ" value={bookingMode === 'group' ? 'Theo sức chứa' : 'Khám riêng với bác sĩ'} />}
          </dl>

          <div className="mt-5 space-y-4 border-t border-slate-100 light:border-app-border pt-5">
            <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
              Lý do khám <span className="text-red-500">*</span>
              <textarea
                value={reason}
                onChange={(event) => onReasonChange(event.target.value)}
                maxLength={500}
                rows={3}
                placeholder="Mô tả ngắn triệu chứng hoặc nhu cầu khám"
                className="mt-2 w-full rounded-xl border border-slate-300 light:border-app-border px-3 py-2 text-sm font-normal outline-none focus:border-sky-500 light:focus:border-app-primary focus:ring-2 focus:ring-sky-100"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700 light:text-app-text">
              Ghi chú thêm <span className="font-normal text-slate-400 light:text-app-secondary">(không bắt buộc)</span>
              <textarea
                value={patientNote}
                onChange={(event) => onPatientNoteChange(event.target.value)}
                maxLength={500}
                rows={2}
                placeholder="Thông tin bạn muốn gửi trước cho cơ sở khám"
                className="mt-2 w-full rounded-xl border border-slate-300 light:border-app-border px-3 py-2 text-sm font-normal outline-none focus:border-sky-500 light:focus:border-app-primary focus:ring-2 focus:ring-sky-100"
              />
            </label>
          </div>

          <div className="mt-5 border-t border-slate-100 light:border-app-border pt-4">
            <div className="flex items-center justify-between text-sm text-slate-600 light:text-app-secondary">
              <span>Phí dịch vụ tham khảo</span>
              <span className="font-bold text-slate-900 light:text-app-text">{formatPrice(price)}</span>
            </div>
            <p className="mt-2 flex items-start gap-2 text-xs leading-5 text-slate-500 light:text-app-secondary">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> Chi phí cuối cùng do cơ sở khám xác nhận.
            </p>
          </div>

          <button
            type="button"
            onClick={onBook}
            disabled={isBooking}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-sky-700 light:bg-app-primary-hover py-3.5 font-bold text-white shadow-md shadow-sky-700/20 light:shadow-app-primary/20 transition-colors hover:bg-sky-800 light:hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isBooking ? <><TypewriterLoader /> Đang xử lý...</> : <><CalendarDays className="h-4 w-4" /> {submitLabel}</>}
          </button>
        </div>
      </div>
    </aside>
  );
}

function SummaryRow({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="grid grid-cols-[88px_1fr] items-start gap-3">
      <dt className="text-slate-500 light:text-app-secondary">{label}</dt>
      <dd className={accent ? 'font-bold text-sky-700 light:text-app-primary' : 'font-semibold text-slate-900 light:text-app-text'}>{value || 'Chưa chọn'}</dd>
    </div>
  );
}
