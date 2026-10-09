import { FormEvent, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import {
  createDoctorSchedule,
  Doctor,
  Schedule,
  ScheduleApiError,
} from '../../../features/appointment-booking/api';
import { formatDateVN } from '../../../features/appointment-booking/dateValidation';
import { DateInputVN } from '../../../components/DateInputVN';

interface CreateScheduleModalProps {
  doctor: Doctor;
  defaultDate: string;
  onClose: () => void;
  onCreated: (schedule: Schedule) => void;
}

function toIsoString(date: string, time: string): string {
  return new Date(`${date}T${time}:00`).toISOString();
}

export function CreateScheduleModal({ doctor, defaultDate, onClose, onCreated }: CreateScheduleModalProps) {
  const facilities = doctor.facilities || [];
  const services = (doctor.services || []).filter((item) => item.active !== false);
  const [date, setDate] = useState(defaultDate);
  const [facilityId, setFacilityId] = useState(facilities[0]?.facility_id || '');
  const [serviceId, setServiceId] = useState(services[0]?.service_id || '');
  const [startTime, setStartTime] = useState('08:00');
  const [endTime, setEndTime] = useState('12:00');
  const [capacity, setCapacity] = useState('5');
  const [status, setStatus] = useState<'available' | 'blocked' | 'inactive'>('available');
  const [busyReason, setBusyReason] = useState<'consultation' | 'other_commitment'>('other_commitment');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => setDate(defaultDate), [defaultDate]);

  const selectedService = services.find((item) => item.service_id === serviceId);
  const needsService = status === 'available' || (status === 'blocked' && busyReason === 'consultation');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!facilityId) {
      setError('Vui lòng chọn cơ sở khám được phân công cho bác sĩ.');
      return;
    }
    if (needsService && !selectedService) {
      setError('Vui lòng chọn dịch vụ bác sĩ được phân công.');
      return;
    }
    if (endTime <= startTime) {
      setError('Kết thúc phải sau Bắt đầu.');
      return;
    }
    const numericCapacity = selectedService?.booking_mode === 'doctor_visit' ? 1 : Number(capacity);
    if (status === 'available' && (!Number.isInteger(numericCapacity) || numericCapacity < 1)) {
      setError('Số lượt tiếp nhận phải là số nguyên lớn hơn 0.');
      return;
    }

    setSubmitting(true);
    try {
      const schedule = await createDoctorSchedule({
        doctor_id: doctor.id,
        facility_id: facilityId,
        service_id: selectedService?.service_id || null,
        starts_at: toIsoString(date, startTime),
        ends_at: toIsoString(date, endTime),
        capacity: status === 'available' ? numericCapacity : 0,
        status,
        busy_reason: status === 'blocked' ? busyReason : null,
        note: note.trim() || undefined,
      });
      onCreated(schedule);
    } catch (cause) {
      if (cause instanceof ScheduleApiError && cause.status === 409) {
        setError(`Không thể tạo lịch do trùng thời gian hoặc dịch vụ không hợp lệ: ${cause.message}`);
      } else if (cause instanceof Error) {
        setError(cause.message);
      } else {
        setError('Không thể tạo lịch. Vui lòng thử lại.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = (value: 'available' | 'blocked' | 'inactive') => {
    setStatus(value);
    if (value === 'blocked') {
      setBusyReason('other_commitment');
    } else if (value === 'available' && selectedService?.booking_mode === 'doctor_visit') {
      setCapacity('1');
    }
  };

  const handleServiceChange = (value: string) => {
    setServiceId(value);
    const service = services.find((item) => item.service_id === value);
    if (service?.booking_mode === 'doctor_visit') setCapacity('1');
    else if (status === 'available') setCapacity('5');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} className="flex max-h-[calc(100dvh-2rem)] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-7">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Tạo lịch bác sĩ</h2>
            <p className="mt-1 text-xs text-slate-500">{doctor.title ? `${doctor.title} ` : ''}{doctor.full_name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Đóng">
            <X size={20} />
          </button>
        </div>

        <div className="min-h-0 space-y-5 overflow-y-auto px-5 py-5 sm:px-7">
          <section className="grid gap-4 rounded-xl border border-slate-200 p-4 sm:grid-cols-2">
            <div>
              <label htmlFor="schedule-facility" className="mb-1 block text-xs font-bold text-slate-600">Cơ sở khám *</label>
              <select id="schedule-facility" value={facilityId} onChange={(event) => setFacilityId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required>
                <option value="">Chọn cơ sở khám</option>
                {facilities.map((assignment) => (
                  <option key={assignment.facility_id} value={assignment.facility_id}>
                    {assignment.facility?.name || 'Cơ sở chưa cập nhật'}{assignment.room ? ` - Phòng ${assignment.room}` : ''}
                  </option>
                ))}
              </select>
              {facilities.length === 0 && <p className="mt-1 text-xs text-amber-600">Bác sĩ chưa được gán cơ sở khám.</p>}
            </div>
            <div>
              <label htmlFor="schedule-status" className="mb-1 block text-xs font-bold text-slate-600">Loại lịch *</label>
              <select id="schedule-status" value={status} onChange={(event) => handleStatusChange(event.target.value as typeof status)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="available">Lịch khám</option>
                <option value="blocked">Bác sĩ bận</option>
                <option value="inactive">Chưa kích hoạt</option>
              </select>
            </div>
          </section>

          {status !== 'blocked' || busyReason === 'consultation' ? (
            <section className="grid gap-4 rounded-xl border border-slate-200 p-4 sm:grid-cols-2">
              <div>
                <label htmlFor="schedule-service" className="mb-1 block text-xs font-bold text-slate-600">Dịch vụ khám {needsService ? '*' : ''}</label>
                <select id="schedule-service" value={serviceId} onChange={(event) => handleServiceChange(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required={needsService}>
                  <option value="">Chọn dịch vụ</option>
                  {services.map((item) => (
                    <option key={item.service_id} value={item.service_id}>
                      {item.name} — {item.booking_mode === 'doctor_visit' ? 'Khám riêng với bác sĩ' : 'Khám nhóm'}
                    </option>
                  ))}
                </select>
                {needsService && services.length === 0 && <p className="mt-1 text-xs text-amber-600">Bác sĩ chưa được gán dịch vụ khám.</p>}
              </div>
              {selectedService && (
                <div className="flex items-end pb-2 text-sm font-medium text-sky-800">
                  Hình thức: {selectedService.booking_mode === 'doctor_visit' ? 'Khám riêng với bác sĩ' : 'Khám nhóm'}
                </div>
              )}
            </section>
          ) : null}

          {status === 'blocked' && (
            <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
              <label htmlFor="schedule-busy-reason" className="mb-1 block text-xs font-bold text-slate-700">Lý do bác sĩ bận *</label>
              <select id="schedule-busy-reason" value={busyReason} onChange={(event) => setBusyReason(event.target.value as typeof busyReason)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="other_commitment">Có lịch khác</option>
                <option value="consultation">Bác sĩ đang khám</option>
              </select>
              <p className="mt-1 text-xs text-slate-500">Chọn dịch vụ khám nếu lịch bận do bác sĩ đang khám.</p>
            </section>
          )}

          <section className="rounded-xl border border-slate-200 p-4">
            <h3 className="mb-3 text-sm font-bold text-slate-800">Thời gian</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="schedule-date" className="mb-1 block text-xs font-bold text-slate-600">Ngày khám *</label>
                <DateInputVN id="schedule-date" value={date} onChange={(event) => setDate(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
                {date && <span className="mt-1 block text-xs font-medium text-sky-600">{formatDateVN(date)}</span>}
              </div>
              <div>
                <label htmlFor="schedule-start" className="mb-1 block text-xs font-bold text-slate-600">Bắt đầu *</label>
                <input id="schedule-start" type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
              </div>
              <div>
                <label htmlFor="schedule-end" className="mb-1 block text-xs font-bold text-slate-600">Kết thúc *</label>
                <input id="schedule-end" type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
              </div>
            </div>
          </section>

          {status === 'available' && (
            <section className="rounded-xl border border-slate-200 p-4">
              <label htmlFor="schedule-capacity" className="mb-1 block text-xs font-bold text-slate-600">Số lượt tiếp nhận *</label>
              {selectedService?.booking_mode === 'doctor_visit' ? (
                <input id="schedule-capacity" type="number" value="1" readOnly className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600" />
              ) : (
                <input id="schedule-capacity" type="number" min="1" step="1" value={capacity} onChange={(event) => setCapacity(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
              )}
            </section>
          )}

          <section>
            <label htmlFor="schedule-note" className="mb-1 block text-xs font-bold text-slate-600">Ghi chú</label>
            <textarea id="schedule-note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} rows={3} placeholder="Thông tin bổ sung cho lịch..." className="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" />
            <p className="mt-1 text-right text-xs text-slate-400">{note.length}/500</p>
          </section>

          {error && (
            <div className="flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-4 sm:px-7">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200">Hủy</button>
          <button type="submit" disabled={submitting || facilities.length === 0 || (needsService && services.length === 0)} className="flex items-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">
            {submitting ? 'Đang lưu...' : <><CheckCircle2 size={16} /> Tạo lịch</>}
          </button>
        </div>
      </form>
    </div>
  );
}
