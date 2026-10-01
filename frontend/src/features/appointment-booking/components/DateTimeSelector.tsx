import { Building2, CalendarDays, Check, Clock3, Loader2, MapPin, Video } from 'lucide-react';
import clsx from 'clsx';
import { Facility, Schedule } from '../api';

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function formatSlotRange(schedule: Schedule, serviceDuration: number | null): string {
  const startsAt = new Date(schedule.starts_at);
  const endsAt = serviceDuration && serviceDuration > 0
    ? new Date(startsAt.getTime() + serviceDuration * 60 * 1000)
    : new Date(schedule.ends_at);
  return `${formatTime(startsAt.toISOString())} – ${formatTime(endsAt.toISOString())}`;
}

type AppointmentType = 'offline' | 'telehealth';

interface Props {
  selectedDate: string;
  onSelectDate: (date: string) => void;
  selectedType: AppointmentType;
  onSelectType: (type: AppointmentType) => void;
  selectedSlot: string;
  onSelectSlot: (slotId: string) => void;
  schedules?: Schedule[];
  selectedFacility?: Facility;
  serviceDuration?: number | null;
  loading?: boolean;
}

export function DateTimeSelector({
  selectedDate,
  onSelectDate,
  selectedType,
  onSelectType,
  selectedSlot,
  onSelectSlot,
  schedules = [],
  selectedFacility,
  serviceDuration = null,
  loading = false,
}: Props) {
  const dateOptions = Array.from({ length: 7 }, (_, index) => {
    const value = new Date();
    value.setHours(0, 0, 0, 0);
    value.setDate(value.getDate() + index);
    return {
      value: formatLocalDate(value),
      day: value.toLocaleDateString('vi-VN', { weekday: 'short' }).replace('.', ''),
      isToday: index === 0,
      label: value.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }),
    };
  });

  const slotGroups = [
    { label: 'Buổi sáng', slots: schedules.filter((schedule) => new Date(schedule.starts_at).getHours() < 12) },
    { label: 'Buổi chiều và tối', slots: schedules.filter((schedule) => new Date(schedule.starts_at).getHours() >= 12) },
  ].filter((group) => group.slots.length > 0);

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-2 border-b border-slate-100 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-600">Bước 4</p>
          <h2 className="mt-1 flex items-center gap-2 text-lg font-bold text-slate-900">
            <CalendarDays className="h-5 w-5 text-sky-600" /> Chọn ngày và khung giờ
          </h2>
        </div>
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500">
          <Clock3 className="h-4 w-4" /> Lịch trống theo thời gian thực
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-5 xl:grid-cols-7">
        {dateOptions.map((date) => {
          const isSelected = date.value === selectedDate;
          return (
            <button
              type="button"
              key={date.value}
              onClick={() => onSelectDate(date.value)}
              className={clsx(
                'rounded-xl border px-2 py-3 text-center transition-colors',
                isSelected ? 'border-sky-600 bg-sky-700 text-white shadow-sm' : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-sky-300 hover:bg-sky-50',
              )}
            >
              <span className={clsx('block text-xs font-semibold', isSelected ? 'text-sky-100' : 'text-slate-500')}>{date.day}</span>
              {date.isToday && <span className={clsx('mt-0.5 block text-[10px]', isSelected ? 'text-sky-100' : 'text-sky-600')}>Hôm nay</span>}
              <span className="mt-1 block text-lg font-bold">{date.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onSelectType('offline')}
          className={clsx('flex items-center justify-center gap-2 rounded-xl border p-3 text-sm font-semibold transition-colors', selectedType === 'offline' ? 'border-sky-300 bg-sky-50 text-sky-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50')}
        >
          <Building2 className="h-4 w-4" /> Khám tại cơ sở
        </button>
        <button
          type="button"
          onClick={() => onSelectType('telehealth')}
          className={clsx('flex items-center justify-center gap-2 rounded-xl border p-3 text-sm font-semibold transition-colors', selectedType === 'telehealth' ? 'border-sky-300 bg-sky-50 text-sky-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50')}
        >
          <Video className="h-4 w-4" /> Khám trực tuyến
        </button>
      </div>

      <div className="mt-7 space-y-6">
        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin text-sky-600" /> Đang tải khung giờ còn chỗ...
          </div>
        )}
        {!loading && slotGroups.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm leading-6 text-slate-500">
            Chưa có khung giờ được cơ sở công bố trong ngày đã chọn. Vui lòng thử ngày khác hoặc chọn cơ sở khác.
          </div>
        )}
        {!loading && slotGroups.map((group) => (
          <div key={group.label}>
            <h3 className="mb-3 text-sm font-bold text-slate-700">{group.label}</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              {group.slots.map((schedule) => {
                const isDemo = schedule.source_system === 'ui-demo';
                const remainingCapacity = schedule.remaining_capacity ?? schedule.capacity;
                const hasCapacity = typeof remainingCapacity === 'number';
                const isAvailable = isDemo || (schedule.status === 'available' && (!hasCapacity || remainingCapacity > 0));
                const isSelected = selectedSlot === schedule.id;
                return (
                  <button
                    type="button"
                    key={schedule.id}
                    disabled={!isAvailable}
                    aria-pressed={isSelected}
                    onClick={() => isAvailable && onSelectSlot(schedule.id)}
                    className={clsx(
                      'relative rounded-xl border px-3 py-3 text-center transition-all',
                      !isAvailable && 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400',
                      isAvailable && !isSelected && 'border-sky-100 bg-sky-50/60 text-sky-900 hover:border-sky-300 hover:bg-sky-50',
                      isSelected && 'border-sky-700 bg-sky-700 text-white shadow-md ring-2 ring-sky-200',
                    )}
                  >
                    {isSelected && <Check className="absolute right-2 top-2 h-4 w-4 text-emerald-300" />}
                    <span className="block font-bold">{formatSlotRange(schedule, serviceDuration)}</span>
                    <span className={clsx('mt-1 block text-xs', isSelected ? 'text-sky-100' : isAvailable ? 'text-sky-600' : 'text-slate-400')}>
                      {isAvailable ? (isDemo || !hasCapacity ? 'Còn trống' : `${remainingCapacity} chỗ trống`) : 'Không còn chỗ'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-7 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-sky-600 shadow-sm">
            {selectedType === 'offline' ? <MapPin className="h-4 w-4" /> : <Video className="h-4 w-4" />}
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-900">{selectedType === 'offline' ? 'Địa điểm khám' : 'Hình thức trực tuyến'}</h3>
            {selectedType === 'offline' ? (
              selectedFacility ? (
                <>
                  <p className="mt-1 text-sm text-slate-700">{selectedFacility.name}</p>
                  {selectedFacility.address && <p className="mt-1 text-xs leading-5 text-slate-500">{selectedFacility.address}</p>}
                  {selectedFacility.phone && <p className="mt-1 text-xs text-slate-500">Điện thoại: {selectedFacility.phone}</p>}
                </>
              ) : <p className="mt-1 text-sm text-slate-500">Cơ sở sẽ được xác định theo khung giờ bạn chọn.</p>
            ) : <p className="mt-1 text-sm leading-5 text-slate-600">Thông tin kết nối sẽ được gửi sau khi lịch hẹn được xác nhận.</p>}
          </div>
        </div>
      </div>
    </section>
  );
}
