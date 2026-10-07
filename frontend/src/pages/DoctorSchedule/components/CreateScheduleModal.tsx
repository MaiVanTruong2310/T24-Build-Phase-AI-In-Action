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

export function CreateScheduleModal({
  doctor,
  defaultDate,
  onClose,
  onCreated,
}: CreateScheduleModalProps) {
  const facilities = doctor.facilities || [];
  const [date, setDate] = useState(defaultDate);
  const [facilityId, setFacilityId] = useState(facilities[0]?.facility_id || '');
  const [startTime, setStartTime] = useState('08:00');
  const [endTime, setEndTime] = useState('12:00');
  const [capacity, setCapacity] = useState('5');
  const [status, setStatus] = useState<'available' | 'blocked' | 'inactive'>('available');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setDate(defaultDate);
  }, [defaultDate]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!facilityId) {
      setError('Bác sĩ chưa được gán cơ sở. Hãy gán facility trước khi tạo lịch.');
      return;
    }
    if (endTime <= startTime) {
      setError('Giờ kết thúc phải sau giờ bắt đầu.');
      return;
    }
    const numericCapacity = Number(capacity);
    if (!Number.isInteger(numericCapacity) || numericCapacity < 0) {
      setError('Sức chứa phải là số nguyên lớn hơn hoặc bằng 0.');
      return;
    }

    setSubmitting(true);
    try {
      const schedule = await createDoctorSchedule({
        doctor_id: doctor.id,
        facility_id: facilityId,
        starts_at: toIsoString(date, startTime),
        ends_at: toIsoString(date, endTime),
        capacity: numericCapacity,
        status,
      });
      onCreated(schedule);
    } catch (cause) {
      if (cause instanceof ScheduleApiError && cause.status === 409) {
        setError(`Không thể tạo lịch vì bị trùng thời gian: ${cause.message}`);
      } else if (cause instanceof Error) {
        setError(cause.message);
      } else {
        setError('Không thể tạo lịch. Vui lòng thử lại.');
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
            <h2 className="text-lg font-bold text-slate-800">Tạo lịch khám cho bác sĩ</h2>
            <p className="mt-1 text-xs text-slate-500">Nhập đầy đủ cơ sở, ngày và khoảng thời gian làm việc.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Đóng">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="rounded-xl bg-sky-50 p-3 text-sm text-sky-900">
            <p className="font-bold">{doctor.title ? `${doctor.title} ` : ''}{doctor.full_name}</p>
            <p className="mt-1 text-xs text-sky-700">Mã bác sĩ: {doctor.code}</p>
          </div>

          <div>
            <label htmlFor="schedule-facility" className="mb-1 block text-xs font-bold text-slate-600">Cơ sở khám *</label>
            <select id="schedule-facility" value={facilityId} onChange={(event) => setFacilityId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required>
              <option value="">Chọn cơ sở</option>
              {facilities.map((assignment) => (
                <option key={assignment.facility_id} value={assignment.facility_id}>
                  {assignment.facility?.name || assignment.facility_id}{assignment.room ? ` - Phòng ${assignment.room}` : ''}
                </option>
              ))}
            </select>
            {facilities.length === 0 && <p className="mt-1 text-xs text-amber-600">Bác sĩ hiện chưa có facility hợp lệ.</p>}
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="schedule-date" className="block text-xs font-bold text-slate-600">
                Ngày khám * <span className="font-normal text-slate-400">(dd/mm/yyyy)</span>
              </label>
              {date && (
                <span className="text-xs font-medium text-sky-600">
                  {formatDateVN(date)}
                </span>
              )}
            </div>
            <DateInputVN id="schedule-date" value={date} onChange={(event) => setDate(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="schedule-start" className="mb-1 block text-xs font-bold text-slate-600">Bắt đầu *</label>
              <input id="schedule-start" type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
            </div>
            <div>
              <label htmlFor="schedule-end" className="mb-1 block text-xs font-bold text-slate-600">Kết thúc *</label>
              <input id="schedule-end" type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="schedule-capacity" className="mb-1 block text-xs font-bold text-slate-600">Số lượt tối đa *</label>
              <input id="schedule-capacity" type="number" min="0" step="1" value={capacity} onChange={(event) => setCapacity(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
            </div>
            <div>
              <label htmlFor="schedule-status" className="mb-1 block text-xs font-bold text-slate-600">Trạng thái</label>
              <select id="schedule-status" value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="available">Sẵn sàng nhận đặt lịch</option>
                <option value="blocked">Tạm khóa</option>
                <option value="inactive">Chưa kích hoạt</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-6 py-4">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200">Hủy</button>
          <button type="submit" disabled={submitting || facilities.length === 0} className="flex items-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">
            {submitting ? 'Đang lưu...' : <><CheckCircle2 size={16} /> Tạo lịch</>}
          </button>
        </div>
      </form>
    </div>
  );
}
