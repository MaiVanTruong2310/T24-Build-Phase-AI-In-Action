import { FormEvent, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import {
  Doctor,
  Schedule,
  ScheduleApiError,
  updateDoctorSchedule,
} from '../../../features/appointment-booking/api';

interface ScheduleDetailModalProps {
  doctor: Doctor;
  schedule: Schedule;
  onClose: () => void;
  onUpdated: (schedule: Schedule) => void;
}

function toDateTimeInput(value: string): string {
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIsoString(value: string): string {
  return new Date(value).toISOString();
}

function locationLabel(doctor: Doctor, schedule: Schedule): string {
  const assignment = doctor.facilities?.find((item) => item.facility_id === schedule.facility_id);
  const facility = assignment?.facility?.name || `Cơ sở ${schedule.facility_id}`;
  return assignment?.room ? `${facility} - Phòng ${assignment.room}` : facility;
}

export function ScheduleDetailModal({ doctor, schedule, onClose, onUpdated }: ScheduleDetailModalProps) {
  const services = (doctor.services || []).filter((item) => item.active !== false);
  const [startsAt, setStartsAt] = useState(toDateTimeInput(schedule.starts_at));
  const [endsAt, setEndsAt] = useState(toDateTimeInput(schedule.ends_at));
  const [serviceId, setServiceId] = useState(schedule.service_id || '');
  const [capacity, setCapacity] = useState(String(schedule.capacity));
  const [status, setStatus] = useState<'available' | 'blocked' | 'inactive'>(schedule.status === 'cancelled' ? 'inactive' : schedule.status);
  const [busyReason, setBusyReason] = useState<'consultation' | 'other_commitment'>(schedule.busy_reason || 'other_commitment');
  const [note, setNote] = useState(schedule.note || '');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const selectedService = services.find((item) => item.service_id === serviceId);

  useEffect(() => {
    setStartsAt(toDateTimeInput(schedule.starts_at));
    setEndsAt(toDateTimeInput(schedule.ends_at));
    setServiceId(schedule.service_id || '');
    setCapacity(String(schedule.capacity));
    setStatus(schedule.status === 'cancelled' ? 'inactive' : schedule.status);
    setBusyReason(schedule.busy_reason || 'other_commitment');
    setNote(schedule.note || '');
  }, [schedule]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (new Date(endsAt) <= new Date(startsAt)) {
      setError('Thời gian kết thúc phải sau thời gian bắt đầu.');
      return;
    }
    const numericCapacity = Number(capacity);
    if (status === 'available' && (!Number.isInteger(numericCapacity) || numericCapacity < 1)) {
      setError('Sức chứa phải là số nguyên lớn hơn hoặc bằng 0.');
      return;
    }

    setSubmitting(true);
    try {
      const updated = await updateDoctorSchedule(schedule.id, {
        starts_at: toIsoString(startsAt),
        ends_at: toIsoString(endsAt),
        service_id: serviceId || null,
        capacity: status === 'blocked' || status === 'inactive' ? 0 : selectedService?.booking_mode === 'doctor_visit' ? 1 : numericCapacity,
        status,
        busy_reason: status === 'blocked' ? busyReason : null,
        note: note.trim() || undefined,
        expected_version: schedule.version,
      });
      onUpdated(updated);
    } catch (cause) {
      if (cause instanceof ScheduleApiError && cause.status === 409) {
        setError(`Không thể cập nhật vì lịch bị conflict hoặc đã được thay đổi: ${cause.message}`);
      } else if (cause instanceof Error) {
        setError(cause.message);
      } else {
        setError('Không thể cập nhật lịch. Vui lòng thử lại.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Chi tiết và cập nhật lịch</h2>
            <p className="mt-1 text-xs text-slate-500">Phiên bản hiện tại: v{schedule.version}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Đóng"><X size={20} /></button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="rounded-xl bg-sky-50 p-3 text-sm text-sky-900">
            <p className="font-bold">{doctor.title ? `${doctor.title} ` : ''}{doctor.full_name}</p>
            <p className="mt-1 text-xs text-sky-700">Mã lịch: {schedule.id}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="detail-start" className="mb-1 block text-xs font-bold text-slate-600">Bắt đầu *</label>
              <input id="detail-start" type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-sky-500" required />
            </div>
            <div>
              <label htmlFor="detail-end" className="mb-1 block text-xs font-bold text-slate-600">Kết thúc *</label>
              <input id="detail-end" type="datetime-local" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-sky-500" required />
            </div>
          </div>

          <div>
            <label htmlFor="detail-service" className="mb-1 block text-xs font-bold text-slate-600">Dịch vụ khám</label>
            <select id="detail-service" value={serviceId} onChange={(event) => setServiceId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required={status === 'available' || (status === 'blocked' && busyReason === 'consultation')}>
              <option value="">Chọn dịch vụ</option>
              {services.map((item) => (
                <option key={item.service_id} value={item.service_id}>{item.name} — {item.booking_mode === 'doctor_visit' ? 'Khám riêng với bác sĩ' : 'Khám nhóm'}</option>
              ))}
            </select>
          </div>

          {status === 'blocked' && (
            <div>
              <label htmlFor="detail-busy-reason" className="mb-1 block text-xs font-bold text-slate-600">Lý do bác sĩ bận</label>
              <select id="detail-busy-reason" value={busyReason} onChange={(event) => setBusyReason(event.target.value as typeof busyReason)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="other_commitment">Có lịch khác</option>
                <option value="consultation">Bác sĩ đang khám</option>
              </select>
            </div>
          )}

          <div>
            <label htmlFor="detail-task" className="mb-1 block text-xs font-bold text-slate-600">Nhiệm vụ</label>
            <input id="detail-task" value="Khám bệnh và tiếp nhận bệnh nhân" readOnly className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600" />
          </div>

          <div>
            <label htmlFor="detail-note" className="mb-1 block text-xs font-bold text-slate-600">Ghi chú</label>
            <textarea id="detail-note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} rows={3} className="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" />
          </div>

          <div>
            <label htmlFor="detail-location" className="mb-1 block text-xs font-bold text-slate-600">Địa điểm</label>
            <input id="detail-location" value={locationLabel(doctor, schedule)} readOnly className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="detail-capacity" className="mb-1 block text-xs font-bold text-slate-600">Số lượt tối đa *</label>
              <input id="detail-capacity" type="number" min="0" step="1" value={capacity} onChange={(event) => setCapacity(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
            </div>
            <div>
              <label htmlFor="detail-status" className="mb-1 block text-xs font-bold text-slate-600">Trạng thái</label>
              <select id="detail-status" value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="available">Sẵn sàng nhận đặt lịch</option>
                <option value="blocked">Tạm khóa</option>
                <option value="inactive">Chưa kích hoạt</option>
              </select>
            </div>
          </div>

          {error && <div className="flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert"><AlertCircle size={18} className="mt-0.5 shrink-0" /><span>{error}</span></div>}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-6 py-4">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200">Đóng</button>
          <button type="submit" disabled={submitting || schedule.status === 'cancelled'} className="flex items-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? 'Đang lưu...' : <><CheckCircle2 size={16} /> Cập nhật lịch</>}</button>
        </div>
      </form>
    </div>
  );
}
