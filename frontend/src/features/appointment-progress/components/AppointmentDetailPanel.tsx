import {
  CalendarClock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  PhoneCall,
  QrCode,
  RefreshCw,
  ShieldCheck,
  Stethoscope,
  UserRoundCheck,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import { Booking } from '../../appointment-booking/api';
import { AppointmentDisplayData } from '../types';

interface Props {
  booking: Booking | null;
  display: AppointmentDisplayData | null;
  isCancelling: boolean;
  onCancel: () => void;
  onReschedule: () => void;
}

export function AppointmentDetailPanel({ booking, display, isCancelling, onCancel, onReschedule }: Props) {
  if (!booking || !display) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-dashed border-slate-300 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-8 text-center text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">
        Chọn một lịch hẹn hoặc gói khám để xem chi tiết tiến trình.
      </div>
    );
  }

  const isPackage = display.bookingType === 'package';
  const isCoord = display.bookingType === 'coordination';
  const isDoctor = display.bookingType === 'doctor_visit';
  const canModify = booking.status === 'pending_approval' || booking.status === 'confirmed';

  return (
    <aside className="space-y-5 xl:sticky xl:top-6">
      <section className="overflow-hidden rounded-3xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface shadow-sm">
        {/* Header */}
        <div className="border-b border-slate-100 dark:border-app-border light:border-app-border p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <span className={clsx('inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-bold shadow-2xs', display.typeBadge.bg, display.typeBadge.text, display.typeBadge.border)}>
                <span>{display.typeBadge.icon}</span>
                <span>{display.typeBadge.label}</span>
              </span>
              <h2 className="mt-2 text-xl font-bold text-slate-900 dark:text-app-text light:text-app-text leading-snug">
                {display.primaryTitle}
              </h2>
              <p className="mt-1 text-sm font-semibold text-sky-700 dark:text-sky-300 light:text-app-primary">
                {display.secondaryTitle}
              </p>
            </div>
            <div className="shrink-0 rounded-2xl p-3 border shadow-2xs bg-slate-50 dark:bg-app-surface border-slate-200 dark:border-app-border">
              {isPackage ? (
                <Package className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              ) : isCoord ? (
                <UserRoundCheck className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
              ) : (
                <Stethoscope className="h-6 w-6 text-sky-600 dark:text-sky-400" />
              )}
            </div>
          </div>
        </div>

        <div className="space-y-5 p-5">
          {/* Trạng thái hiện tại */}
          {booking.status === 'confirmed' ? (
            <div className="rounded-2xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 p-4">
              <div className="flex items-center gap-3">
                <QrCode className="h-6 w-6 text-teal-700 dark:text-teal-300" />
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-teal-800 dark:text-teal-300">Mã check-in tiếp đón</p>
                  <p className="mt-1 font-mono font-bold text-slate-900 dark:text-app-text">#{booking.id.slice(0, 8).toUpperCase()}</p>
                </div>
              </div>
              <p className="mt-3 text-xs leading-5 text-teal-900 dark:text-teal-200">
                Xuất trình mã hoặc số điện thoại tại quầy lễ tân để được phân luồng ưu tiên.
              </p>
            </div>
          ) : booking.status === 'cancelled' ? (
            <div className="rounded-2xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/50 p-4 text-sm leading-6 text-rose-800 dark:text-rose-300">
              <X className="mr-2 inline h-4 w-4" /> Phiếu này đã được hủy và lưu trong lịch sử.
            </div>
          ) : booking.status === 'expired' ? (
            <div className="rounded-2xl border border-slate-200 dark:border-app-border bg-slate-100 dark:bg-app-muted p-4 text-sm leading-6 text-slate-700 dark:text-app-secondary">
              <X className="mr-2 inline h-4 w-4" /> Phiếu đã hết hạn duyệt và không thể thao tác tiếp.
            </div>
          ) : booking.status === 'rejected' ? (
            <div className="rounded-2xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/50 p-4 text-sm leading-6 text-rose-800 dark:text-rose-300">
              <X className="mr-2 inline h-4 w-4" /> Yêu cầu đã bị từ chối do khung giờ hoặc bác sĩ không khả dụng.
            </div>
          ) : (
            <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 p-4 text-sm leading-6 text-amber-900 dark:text-amber-200">
              <ShieldCheck className="mr-2 inline h-4 w-4 text-amber-600 dark:text-amber-400" />
              {isPackage
                ? 'Đơn đăng ký gói khám đang được chuyên viên y tế tiếp nhận. Bạn sẽ sớm nhận được cuộc gọi tư vấn chuẩn bị và chốt lịch.'
                : isCoord
                ? 'Phiếu triệu chứng đang được trợ lý y tế & bác sĩ điều phối thẩm định để sắp xếp chuyên khoa tối ưu.'
                : 'Lịch hẹn đang chờ bác sĩ và phòng khám tiếp nhận và xác nhận lịch hẹn.'}
            </div>
          )}

          {/* Chi tiết thông số lịch */}
          <div className="grid gap-3.5 rounded-2xl border border-slate-100 dark:border-app-border light:border-app-border bg-slate-50 dark:bg-app-surface light:bg-app-page p-4 text-xs">
            {/* Thời gian */}
            <div className="flex gap-3">
              <CalendarClock className="mt-0.5 h-4.5 w-4.5 text-sky-700 dark:text-sky-300 light:text-app-primary shrink-0" />
              <div>
                <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">
                  {isPackage ? 'Ngày & Buổi đăng ký' : 'Thời gian hẹn'}
                </p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">
                  {display.startsAtFormatted}
                </p>
                {display.preferredPeriod && (
                  <p className="mt-0.5 text-xs text-sky-700 dark:text-sky-300 font-medium">
                    {display.preferredPeriod === 'morning' ? 'Buổi sáng (07:30 - 11:30)' : 'Buổi chiều (13:30 - 17:00)'}
                  </p>
                )}
                {display.endsAtFormatted && (
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">
                    Kết thúc dự kiến: {display.endsAtFormatted}
                  </p>
                )}
              </div>
            </div>

            {/* Địa điểm */}
            <div className="flex gap-3">
              <MapPin className="mt-0.5 h-4.5 w-4.5 text-sky-700 dark:text-sky-300 light:text-app-primary shrink-0" />
              <div>
                <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">Địa điểm thực hiện</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">{display.facilityName}</p>
              </div>
            </div>

            {/* Bác sĩ (nếu có và là khám BS) */}
            {isDoctor && display.doctorName && (
              <div className="flex gap-3">
                <Stethoscope className="mt-0.5 h-4.5 w-4.5 text-sky-700 dark:text-sky-300 light:text-app-primary shrink-0" />
                <div>
                  <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">Bác sĩ phụ trách</p>
                  <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">{display.doctorName}</p>
                  {display.doctorTitle && (
                    <p className="mt-0.5 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">{display.doctorTitle}</p>
                  )}
                </div>
              </div>
            )}

            {/* Chi phí (nếu có giá dịch vụ) */}
            {display.servicePrice !== undefined && display.servicePrice !== null && (
              <div className="flex gap-3">
                <CreditCard className="mt-0.5 h-4.5 w-4.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">Chi phí tham khảo</p>
                  <p className="mt-0.5 text-sm font-bold text-emerald-600 dark:text-emerald-400">
                    {display.servicePrice.toLocaleString('vi-VN')} đ
                  </p>
                </div>
              </div>
            )}

            {/* Ghi chú / Triệu chứng */}
            {display.notes && (
              <div className="flex gap-3">
                <FileText className="mt-0.5 h-4.5 w-4.5 text-slate-500 shrink-0" />
                <div>
                  <p className="font-bold uppercase tracking-wide text-slate-500 dark:text-app-secondary light:text-app-secondary">Ghi chú & Triệu chứng</p>
                  <p className="mt-0.5 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{display.notes}</p>
                </div>
              </div>
            )}
          </div>

          {/* Dặn dò trước khám tailored per type */}
          <div>
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">
              <FileText className="h-4 w-4 text-sky-700 dark:text-sky-300 light:text-app-primary" />
              {isPackage ? 'Hướng dẫn chuẩn bị trước khi khám gói' : 'Dặn dò trước giờ khám'}
            </h3>
            {display.instructions && display.instructions.length > 0 ? (
              <div className="mt-3 space-y-2">
                {display.instructions.map((inst, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-200 dark:border-app-border bg-slate-50/80 dark:bg-app-surface p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-app-text">
                        <span>{inst.icon || '📌'}</span>
                        <span>{inst.title}</span>
                      </div>
                      {inst.badge && (
                        <span className="rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 text-[10px] px-2 py-0.5 font-semibold">
                          {inst.badge}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-600 dark:text-app-secondary leading-relaxed pl-5">
                      {inst.content}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 rounded-2xl border border-dashed border-slate-300 dark:border-app-border light:border-app-border p-4 text-sm leading-6 text-slate-500 dark:text-app-secondary light:text-app-secondary">
                Chưa có hướng dẫn chuẩn bị thêm cho lịch hẹn này.
              </div>
            )}
          </div>

          {/* Hỗ trợ */}
          <div className="rounded-2xl bg-slate-50 dark:bg-app-surface light:bg-app-page p-4 border border-slate-100 dark:border-app-border">
            <div className="flex items-center gap-3">
              <PhoneCall className="h-5 w-5 text-sky-700 dark:text-sky-300 light:text-app-primary" />
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-app-text light:text-app-text">Tổng đài hỗ trợ VCare+</p>
                <p className="text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">Hotline: 1900 6868 (Miễn phí từ 7:00 - 21:00 hàng ngày)</p>
              </div>
            </div>
          </div>

          {/* Thao tác */}
          {canModify && (
            <div className="flex gap-3 border-t border-slate-100 dark:border-app-border light:border-app-border pt-5">
              <button
                type="button"
                onClick={onReschedule}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-sky-100 dark:bg-sky-950/50 light:bg-app-tint px-3 py-3 text-sm font-bold text-sky-700 dark:text-sky-300 light:text-app-primary hover:bg-sky-200 dark:hover:bg-sky-950/50 light:hover:bg-app-tint transition"
              >
                <RefreshCw className="h-4 w-4" />
                {isPackage ? 'Đổi ngày gói' : isCoord ? 'Chọn lại lịch' : 'Đổi lịch hẹn'}
              </button>
              <button
                type="button"
                onClick={onCancel}
                disabled={isCancelling}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 dark:border-rose-800 px-3 py-3 text-sm font-bold text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/50 disabled:cursor-wait disabled:opacity-60 transition"
              >
                <X className="h-4 w-4" />
                {isCancelling ? 'Đang hủy...' : isPackage ? 'Hủy đăng ký' : 'Hủy lịch'}
              </button>
            </div>
          )}
        </div>
      </section>
    </aside>
  );
}

