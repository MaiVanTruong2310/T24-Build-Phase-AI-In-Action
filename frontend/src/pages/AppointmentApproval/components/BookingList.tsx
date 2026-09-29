import { CalendarCheck, Loader2 } from 'lucide-react';
import type { PendingBooking } from '../api';
import { BookingCard } from './BookingCard';

interface BookingListProps {
  bookings: PendingBooking[];
  isRefreshing: boolean;
  expandedId: string | null;
  onToggleExpand: (id: string) => void;
  onOpenDetail: (id: string) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  actionId: string | null;
}

export function BookingList({
  bookings,
  isRefreshing,
  expandedId,
  onToggleExpand,
  onOpenDetail,
  onApprove,
  onReject,
  actionId,
}: BookingListProps) {
  if (isRefreshing) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-slate-400">
        <Loader2 size={32} className="animate-spin text-sky-500 mb-3" />
        <p className="text-sm font-semibold">Đang tải dữ liệu mới nhất...</p>
      </div>
    );
  }

  if (bookings.length === 0) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-slate-400">
        <CalendarCheck size={48} className="mb-3 opacity-40" />
        <p className="text-base font-semibold text-slate-500">Không có lịch hẹn nào</p>
        <p className="text-sm mt-1">Thay đổi bộ lọc hoặc tìm kiếm để hiển thị kết quả.</p>
      </div>
    );
  }

  return (
    <>
      {bookings.map(booking => (
        <BookingCard
          key={booking.id}
          booking={booking}
          isExpanded={expandedId === booking.id}
          onToggle={() => onToggleExpand(booking.id)}
          onOpenDetail={() => onOpenDetail(booking.id)}
          onApprove={() => onApprove(booking.id)}
          onReject={() => onReject(booking.id)}
          isActioning={actionId === booking.id}
        />
      ))}
    </>
  );
}
