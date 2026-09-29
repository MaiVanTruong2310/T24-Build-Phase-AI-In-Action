import { memo } from 'react';
import { Stethoscope, Star, MessageSquare } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { openChat } from '../../app/store';
import type { MatchedDoctor } from './types';

interface Props {
  doctors: MatchedDoctor[];
}

export const MatchedDoctorsCard = memo(function MatchedDoctorsCard({ doctors }: Props) {
  const dispatch = useDispatch();

  const handleBookAndChat = () => {
    dispatch(openChat());
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-bold text-slate-900">
          <Stethoscope className="h-4 w-4 text-sky-700" />
          <span>Bác sĩ Chuyên khoa Tiếp nhận Phù hợp</span>
        </h3>
        <span className="text-xs text-slate-400 font-medium hidden sm:inline">
          Sắp xếp theo độ phù hợp lâm sàng
        </span>
      </div>

      {/* ─── Doctors Grid ──────────────────────────────────────── */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {doctors.map((doctor) => {
          const isPrimary = doctor.isPriority;

          return (
            <div
              key={doctor.id}
              className={`flex flex-col justify-between rounded-xl border p-4 transition ${
                isPrimary
                  ? 'border-sky-200 bg-sky-50/30'
                  : 'border-slate-200 bg-slate-50/40'
              }`}
            >
              {/* Doctor Details */}
              <div className="flex items-start gap-3">
                <img
                  src={doctor.avatarUrl}
                  alt={doctor.name}
                  className="h-12 w-12 rounded-xl object-cover border border-slate-200 shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="flex items-center gap-0.5 font-bold text-amber-500">
                      <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                      {doctor.rating}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      ({doctor.reviewsCount})
                    </span>
                  </div>

                  <h4 className="mt-0.5 truncate text-xs sm:text-sm font-bold text-slate-900">
                    {doctor.title} {doctor.name}
                  </h4>

                  <p className="truncate text-xs font-medium text-sky-700">
                    {doctor.specialty}
                  </p>

                  <p className="mt-1 text-[11px] font-medium text-slate-500">
                    {doctor.nextSlot}
                  </p>
                </div>
              </div>

              {/* Action Button */}
              <button
                type="button"
                onClick={handleBookAndChat}
                className={`mt-3.5 flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold shadow-sm transition active:scale-95 ${
                  isPrimary
                    ? 'bg-sky-700 text-white hover:bg-sky-800'
                    : 'bg-sky-100 text-sky-800 hover:bg-sky-200'
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Đặt lịch & Trao đổi qua Chat AI</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
});
