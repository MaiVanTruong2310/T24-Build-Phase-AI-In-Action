import { FormEvent, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import {
  createDoctorSchedule,
  Doctor,
  fetchPatients,
  PatientOption,
  Schedule,
  ScheduleApiError,
} from '../../../features/appointment-booking/api';

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
  const [serviceId, setServiceId] = useState(doctor.services?.[0]?.service_id || '');
  const [specialtyId, setSpecialtyId] = useState(doctor.specialties?.[0]?.specialty_id || '');
  const [patientMode, setPatientMode] = useState<'none' | 'registered' | 'guest'>('none');
  const [patientId, setPatientId] = useState('');
  const [patients, setPatients] = useState<PatientOption[]>([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [guestName, setGuestName] = useState('');
  const [guestEmail, setGuestEmail] = useState('');
  const [guestPhone, setGuestPhone] = useState('');
  const [startTime, setStartTime] = useState('08:00');
  const [endTime, setEndTime] = useState('12:00');
  const [capacity, setCapacity] = useState('5');
  const [status, setStatus] = useState<'available' | 'blocked' | 'inactive'>('available');
  const [scheduleType, setScheduleType] = useState<'consultation' | 'busy' | 'leave' | 'other'>('consultation');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const selectedService = doctor.services?.find((item) => item.service_id === serviceId);
  const supportsDirectPatientBooking = selectedService?.booking_mode === 'doctor_visit';

  useEffect(() => {
    setDate(defaultDate);
  }, [defaultDate]);

  useEffect(() => {
    if (scheduleType !== 'consultation') {
      setServiceId('');
      setPatientMode('none');
      setPatientId('');
      setCapacity('0');
      setStatus('blocked');
    } else {
      setServiceId((current) => current || doctor.services?.[0]?.service_id || '');
      setCapacity((current) => current === '0' ? '5' : current);
      setStatus((current) => current === 'blocked' ? 'available' : current);
    }
  }, [doctor.services, scheduleType]);

  useEffect(() => {
    if (!supportsDirectPatientBooking && patientMode !== 'none') {
      setPatientMode('none');
      setPatientId('');
    }
  }, [patientMode, supportsDirectPatientBooking]);

  useEffect(() => {
    if (patientMode !== 'registered') return;
    let active = true;
    setLoadingPatients(true);
    fetchPatients()
      .then((values) => {
        if (active) setPatients(values);
      })
      .catch(() => {
        if (active) setError('Không thể tải danh sách bệnh nhân. Vui lòng thử lại.');
      })
      .finally(() => {
        if (active) setLoadingPatients(false);
      });
    return () => {
      active = false;
    };
  }, [patientMode]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (scheduleType === 'consultation' && !facilityId) {
      setError('Bác sĩ chưa được gán cơ sở. Hãy gán facility trước khi tạo lịch.');
      return;
    }
    if (scheduleType === 'consultation' && !serviceId) {
      setError('Vui lòng chọn dịch vụ để backend xác định loại lịch.');
      return;
    }
    if (scheduleType === 'consultation' && patientMode === 'registered' && !patientId) {
      setError('Vui lòng chọn bệnh nhân.');
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
      const result = await createDoctorSchedule({
        doctor_id: doctor.id,
        facility_id: facilityId || undefined,
        service_id: scheduleType === 'consultation' ? serviceId : undefined,
        specialty_id: scheduleType === 'consultation' ? specialtyId || undefined : undefined,
        starts_at: toIsoString(date, startTime),
        ends_at: toIsoString(date, endTime),
        capacity: scheduleType === 'consultation' ? numericCapacity : 0,
        status: scheduleType === 'consultation' ? status : 'blocked',
        type: scheduleType,
        note: note.trim() || undefined,
        patient_id: scheduleType === 'consultation' && patientMode === 'registered' ? patientId : undefined,
        guest_patient: scheduleType === 'consultation' && patientMode === 'guest' ? {
          full_name: guestName,
          email: guestEmail,
          phone: guestPhone,
        } : undefined,
      });
      onCreated(result.schedule);
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
            <label htmlFor="schedule-type" className="mb-1 block text-xs font-bold text-slate-600">Loại lịch *</label>
            <select id="schedule-type" value={scheduleType} onChange={(event) => setScheduleType(event.target.value as typeof scheduleType)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
              <option value="consultation">Khám</option>
              <option value="busy">Bận</option>
              <option value="leave">Nghỉ phép</option>
              <option value="other">Khác</option>
            </select>
          </div>

          {scheduleType === 'consultation' && <div>
            <label htmlFor="schedule-service" className="mb-1 block text-xs font-bold text-slate-600">Dịch vụ *</label>
            <select id="schedule-service" value={serviceId} onChange={(event) => setServiceId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required>
              <option value="">Chọn dịch vụ</option>
              {(doctor.services || []).map((item) => <option key={item.service_id} value={item.service_id}>{item.name} ({item.booking_mode === 'doctor_visit' ? 'khám riêng' : 'khám theo sức chứa'})</option>)}
            </select>
          </div>}

          {scheduleType === 'consultation' && <div>
            <label htmlFor="schedule-patient-mode" className="mb-1 block text-xs font-bold text-slate-600">Bệnh nhân (tuỳ chọn)</label>
            {supportsDirectPatientBooking ? (
              <select id="schedule-patient-mode" value={patientMode} onChange={(event) => setPatientMode(event.target.value as typeof patientMode)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                <option value="none">Chỉ tạo lịch, chưa gắn bệnh nhân</option>
                <option value="registered">Bệnh nhân đã có tài khoản</option>
                <option value="guest">Bệnh nhân guest</option>
              </select>
            ) : (
              <p className="rounded-lg bg-slate-50 px-3 py-2.5 text-sm text-slate-600">Dịch vụ theo sức chứa: chỉ tạo lịch, patient sẽ tự chọn và tạo booking.</p>
            )}
          </div>}

          {doctor.specialties && doctor.specialties.length > 0 && (
            <div>
              <label htmlFor="schedule-specialty" className="mb-1 block text-xs font-bold text-slate-600">Chuyên khoa</label>
              <select id="schedule-specialty" value={specialtyId} onChange={(event) => setSpecialtyId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500">
                {doctor.specialties.map((item) => <option key={item.specialty_id} value={item.specialty_id}>{item.name}</option>)}
              </select>
            </div>
          )}

          {patientMode === 'registered' && (
            <select value={patientId} onChange={(event) => setPatientId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required>
              <option value="">{loadingPatients ? 'Đang tải bệnh nhân...' : 'Chọn bệnh nhân'}</option>
              {patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name || 'Chưa có tên'} — {patient.email || patient.phone || patient.id}</option>)}
            </select>
          )}
          {patientMode === 'guest' && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <input value={guestName} onChange={(event) => setGuestName(event.target.value)} placeholder="Tên bệnh nhân" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
              <input type="email" value={guestEmail} onChange={(event) => setGuestEmail(event.target.value)} placeholder="Email" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
              <input value={guestPhone} onChange={(event) => setGuestPhone(event.target.value)} placeholder="Số điện thoại" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
            </div>
          )}

          <div>
            <label htmlFor="schedule-facility" className="mb-1 block text-xs font-bold text-slate-600">Cơ sở khám {scheduleType === 'consultation' ? '*' : '(tuỳ chọn)'}</label>
            <select id="schedule-facility" value={facilityId} onChange={(event) => setFacilityId(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required={scheduleType === 'consultation'}>
              <option value="">{scheduleType === 'consultation' ? 'Chọn cơ sở' : 'Tất cả cơ sở'}</option>
              {facilities.map((assignment) => (
                <option key={assignment.facility_id} value={assignment.facility_id}>
                  {assignment.facility?.name || assignment.facility_id}{assignment.room ? ` - Phòng ${assignment.room}` : ''}
                </option>
              ))}
            </select>
            {facilities.length === 0 && <p className="mt-1 text-xs text-amber-600">Bác sĩ hiện chưa có facility hợp lệ.</p>}
          </div>

          <div>
            <label htmlFor="schedule-date" className="mb-1 block text-xs font-bold text-slate-600">Ngày khám *</label>
            <input id="schedule-date" type="date" value={date} onChange={(event) => setDate(event.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required />
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

          <div>
            <label htmlFor="schedule-note" className="mb-1 block text-xs font-bold text-slate-600">Ghi chú</label>
            <textarea id="schedule-note" value={note} onChange={(event) => setNote(event.target.value)} rows={2} placeholder={scheduleType === 'consultation' ? 'Ghi chú nội bộ (tuỳ chọn)' : 'Lý do bận/nghỉ/khác'} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-500" required={scheduleType !== 'consultation'} />
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
          <button type="submit" disabled={submitting || (scheduleType === 'consultation' && facilities.length === 0)} className="flex items-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50">
            {submitting ? 'Đang lưu...' : <><CheckCircle2 size={16} /> Tạo lịch</>}
          </button>
        </div>
      </form>
    </div>
  );
}
