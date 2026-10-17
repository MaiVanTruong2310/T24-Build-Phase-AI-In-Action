import { AppointmentFilter } from '../types';

interface Props {
  value: AppointmentFilter;
  counts: Record<AppointmentFilter, number>;
  onChange: (value: AppointmentFilter) => void;
}

const filters: Array<{ value: AppointmentFilter; label: string }> = [
  { value: 'all', label: 'Tất cả' },
  { value: 'pending_approval', label: 'Chờ duyệt' },
  { value: 'confirmed', label: 'Đã xác nhận' },
  { value: 'rejected', label: 'Đã từ chối' },
  { value: 'cancelled', label: 'Đã hủy' },
];

export function AppointmentFilters({ value, counts, onChange }: Props) {
  return (
    <div className="ap-filters" role="group" aria-label="Lọc lịch hẹn theo trạng thái">
      {filters.map((filter) => (
        <button key={filter.value} type="button" className="ap-chip" aria-pressed={filter.value === value} onClick={() => onChange(filter.value)}>
          {filter.label}
          <span className="ap-chip__n">{counts[filter.value]}</span>
        </button>
      ))}
    </div>
  );
}
