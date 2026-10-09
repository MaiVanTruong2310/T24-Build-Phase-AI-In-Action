import { Plus, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';
import { Doctor, Schedule } from '../../../features/appointment-booking/api';

export interface WeekDay {
  day: string;
  date: string;
  isToday: boolean;
  iso: string;
}

interface ScheduleMatrixProps {
  doctor: Doctor | null;
  schedules: Schedule[];
  weekDays: WeekDay[];
  onAddSchedule: (date: string) => void;
  onScheduleClick: (schedule: Schedule) => void;
}

const ROW_HEIGHT = 84;
const DAY_MINUTES = 24 * 60;
const SLOT_MINUTES = 2 * 60;
const timelineHeight = ROW_HEIGHT * (DAY_MINUTES / SLOT_MINUTES);

function localDateKey(value: string): string {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function localMinutes(value: string): number {
  const date = new Date(value);
  return date.getHours() * 60 + date.getMinutes();
}

function timeLabel(value: string): string {
  return new Date(value).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function statusLabel(schedule: Schedule): string {
  if (schedule.status === 'cancelled') return 'Đã hủy';
  if (schedule.status === 'blocked') return 'Tạm khóa';
  if (schedule.status === 'inactive') return 'Chưa kích hoạt';
  return schedule.capacity > 0 ? `Còn ${schedule.capacity} lượt` : 'Đã kín';
}

function facilityLabel(schedule: Schedule, doctor: Doctor): string {
  const assignment = doctor.facilities?.find((item) => item.facility_id === schedule.facility_id);
  const facilityName = assignment?.facility?.name || `Cơ sở ${schedule.facility_id.slice(0, 8)}`;
  return assignment?.room ? `${facilityName} • P.${assignment.room}` : facilityName;
}

function serviceLabel(schedule: Schedule, doctor: Doctor): string {
  const service = doctor.services?.find((item) => item.service_id === schedule.service_id);
  if (service) return `${service.name} · ${service.booking_mode === 'doctor_visit' ? 'Khám riêng' : 'Khám nhóm'}`;
  if (schedule.busy_reason === 'consultation') return 'Bác sĩ đang khám';
  if (schedule.busy_reason === 'other_commitment') return 'Có lịch khác';
  return 'Chưa gán dịch vụ';
}

function cardStyle(schedule: Schedule) {
  const startsAt = localMinutes(schedule.starts_at);
  const duration = Math.max(
    1,
    Math.min(DAY_MINUTES - startsAt, (new Date(schedule.ends_at).getTime() - new Date(schedule.starts_at).getTime()) / 60000),
  );
  return {
    top: `${(startsAt / SLOT_MINUTES) * ROW_HEIGHT}px`,
    height: `${Math.max(20, (duration / SLOT_MINUTES) * ROW_HEIGHT)}px`,
  };
}

export function ScheduleMatrix({
  doctor,
  schedules,
  weekDays,
  onAddSchedule,
  onScheduleClick,
}: ScheduleMatrixProps) {
  const timeSlots = Array.from({ length: 12 }, (_, index) => index * 2);

  return (
    <div className="flex min-h-[600px] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 p-4">
        <div>
          <h3 className="text-sm font-bold text-slate-800">Timeline lịch trong ngày</h3>
          <p className="mt-1 text-xs text-slate-500">Mỗi cụm = 2 giờ. Chiều cao lịch tỷ lệ theo thời lượng thực tế.</p>
        </div>
        <div className="flex items-center gap-3 text-xs font-semibold text-slate-600">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-emerald-400" /> Có thể nhận</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-rose-400" /> Khóa/kín</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className={clsx('min-w-[1100px]', weekDays.length === 1 && 'min-w-[360px]')}>
          <div className="grid border-b border-slate-200 bg-slate-50" style={{ gridTemplateColumns: `72px repeat(${weekDays.length}, minmax(190px, 1fr))` }}>
            <div className="border-r border-slate-200 p-3 text-center text-[10px] font-bold uppercase text-slate-500">Giờ</div>
            {weekDays.map((day) => (
              <div key={day.iso} className={clsx('border-r border-slate-100 p-3 text-center last:border-r-0', day.isToday && 'bg-sky-50/60')}>
                <div className={clsx('text-sm font-bold', day.isToday ? 'text-sky-700' : 'text-slate-800')}>{day.day}</div>
                <div className="mt-1 text-[11px] font-medium text-slate-500">{day.date}</div>
                <button onClick={() => onAddSchedule(day.iso)} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-dashed border-sky-200 px-2 py-1 text-[10px] font-bold text-sky-600 hover:bg-sky-50"><Plus size={12} /> Thêm lịch</button>
              </div>
            ))}
          </div>

          {!doctor ? (
            <div className="p-8 text-center text-slate-500">Vui lòng chọn bác sĩ để xem lịch làm việc.</div>
          ) : (
            <div className="grid" style={{ gridTemplateColumns: `72px repeat(${weekDays.length}, minmax(190px, 1fr))` }}>
              <div className="relative border-r border-slate-200 bg-slate-50/60" style={{ height: `${timelineHeight}px` }}>
                {timeSlots.map((hour) => (
                  <div key={hour} className="absolute left-0 right-0 -translate-y-1/2 pr-2 text-right text-[10px] font-semibold text-slate-400" style={{ top: `${(hour / 2) * ROW_HEIGHT}px` }}>
                    {String(hour).padStart(2, '0')}:00
                  </div>
                ))}
              </div>
              {weekDays.map((day) => {
                const daySchedules = schedules
                  .filter((schedule) => localDateKey(schedule.starts_at) === day.iso)
                  .sort((left, right) => new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime());

                return (
                  <div key={day.iso} className={clsx('relative border-r border-slate-100 last:border-r-0', day.isToday && 'bg-sky-50/20')} style={{ height: `${timelineHeight}px` }}>
                    <div className="pointer-events-none absolute inset-0" style={{ backgroundImage: 'linear-gradient(to bottom, #e2e8f0 1px, transparent 1px)', backgroundSize: `100% ${ROW_HEIGHT}px` }} />
                    {timeSlots.map((hour) => <div key={hour} className="pointer-events-none absolute left-0 right-0 border-t border-dashed border-slate-100" style={{ top: `${(hour / 2) * ROW_HEIGHT + ROW_HEIGHT / 2}px` }} />)}
                    {daySchedules.map((schedule) => (
                      <button
                        key={schedule.id}
                        type="button"
                        onClick={() => onScheduleClick(schedule)}
                        className={clsx('absolute z-10 overflow-hidden rounded-lg border px-2 py-1 text-left shadow-sm transition hover:z-20 hover:shadow-md', schedule.status === 'available' && schedule.capacity > 0 ? 'border-emerald-300 bg-emerald-50 text-emerald-900 hover:bg-emerald-100' : 'border-rose-300 bg-rose-50 text-rose-900 hover:bg-rose-100')}
                        style={{ ...cardStyle(schedule), left: '4px', right: '4px' }}
                        title="Xem chi tiết và cập nhật lịch"
                      >
                        <span className="block truncate text-[10px] font-extrabold">{timeLabel(schedule.starts_at)} - {timeLabel(schedule.ends_at)}</span>
                        <span className="block truncate text-[10px] font-semibold">{facilityLabel(schedule, doctor)}</span>
                        <span className="block truncate text-[10px]">{serviceLabel(schedule, doctor)}</span>
                        <span className="block truncate text-[10px]">{statusLabel(schedule)}</span>
                      </button>
                    ))}
                    {daySchedules.length === 0 && <button type="button" onClick={() => onAddSchedule(day.iso)} className="absolute inset-x-3 bottom-3 z-10 rounded-lg border border-dashed border-slate-200 py-2 text-[10px] font-semibold text-slate-400 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-600"><Plus size={13} className="mx-auto" /> Thêm mốc giờ</button>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-slate-200 bg-slate-50 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-100 text-teal-600"><ShieldAlert size={20} /></div>
        <div>
          <h4 className="text-sm font-bold text-slate-800">Theo dõi theo khung 2 giờ</h4>
          <p className="mt-0.5 text-[11px] text-slate-500">Click vào một lịch để xem thời gian, nhiệm vụ, địa điểm và cập nhật trạng thái.</p>
        </div>
      </div>
    </div>
  );
}
