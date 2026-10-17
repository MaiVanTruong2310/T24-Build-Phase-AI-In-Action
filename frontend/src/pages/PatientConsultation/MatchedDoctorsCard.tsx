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
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/65 backdrop-blur-md p-5 sm:p-6 shadow-xl text-slate-100">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h3 className="flex items-center gap-2 text-sm sm:text-base font-semibold text-slate-100">
          <Stethoscope className="h-4 w-4 text-cyan-400" />
          <span>Bác Sĩ Chuyên Khoa Phù Hợp Tiếp Nhận</span>
        </h3>
        <span className="text-xs text-slate-400 hidden sm:inline">
          Phân bổ tự động theo chuyên môn lâm sàng
        </span>
      </div>

      {/* ─── Doctors Grid ──────────────────────────────────────── */}
      <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {doctors.map((doctor) => {
          const isPrimary = doctor.isPriority;

          return (
            <div
              key={doctor.id}
              className={`flex flex-col justify-between rounded-xl border p-4 transition-all duration-300 ${
                isPrimary
                  ? 'border-blue-500/40 bg-blue-950/20'
                  : 'border-slate-800/80 bg-slate-950/50'
              }`}
            >
              {/* Doctor Details */}
              <div className="flex items-start gap-3.5">
                <img
                  src={doctor.avatarUrl}
                  alt={doctor.name}
                  className="h-12 w-12 rounded-xl object-cover border border-slate-700 shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="flex items-center gap-0.5 font-semibold text-amber-400">
                      <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                      {doctor.rating}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      ({doctor.reviewsCount} lượt khám)
                    </span>
                  </div>

                  <h4 className="mt-1 truncate text-xs sm:text-sm font-semibold text-slate-100">
                    {doctor.title} {doctor.name}
                  </h4>

                  <p className="truncate text-xs font-medium text-cyan-400 mt-0.5">
                    {doctor.specialty}
                  </p>

                  <p className="mt-1 text-[11px] font-normal text-emerald-400">
                    {doctor.nextSlot}
                  </p>
                </div>
              </div>

              {/* Action Button */}
              <button
                type="button"
                onClick={handleBookAndChat}
                className={`mt-4 flex w-full items-center justify-center gap-2 rounded-xl py-2 text-xs font-semibold shadow-sm transition active:scale-95 ${
                  isPrimary
                    ? 'btn-clinical-primary'
                    : 'btn-clinical-ghost'
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Đặt Lịch & Hội Chẩn AI</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
});
