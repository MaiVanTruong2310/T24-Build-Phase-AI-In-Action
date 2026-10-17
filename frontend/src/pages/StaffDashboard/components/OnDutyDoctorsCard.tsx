import { Stethoscope, UserPlus } from 'lucide-react';
import { OnDutyDoctor } from '../types';

interface OnDutyDoctorsCardProps {
  doctors: OnDutyDoctor[];
  onDispatchStaff?: () => void;
}

export function OnDutyDoctorsCard({ doctors, onDispatchStaff }: OnDutyDoctorsCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-2xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-teal-50 text-teal-600 flex items-center justify-center">
            <Stethoscope size={15} />
          </div>
          <h3 className="text-sm font-extrabold text-slate-800">Bác sĩ trực chuyên khoa</h3>
        </div>
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
      </div>

      {/* Doctor list */}
      <div className="space-y-2.5">
        {doctors.map((doctor) => {
          return (
            <div
              key={doctor.id}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50/70 hover:bg-slate-100/70 border border-slate-100 transition-colors"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <img
                  src={doctor.avatar}
                  alt={doctor.name}
                  className="w-10 h-10 rounded-full object-cover border border-slate-200 shrink-0"
                />
                <div className="min-w-0">
                  <p className="text-xs font-black text-slate-900 leading-tight truncate">
                    {doctor.name}
                  </p>
                  <p className="text-[11px] text-slate-500 font-medium truncate mt-0.5">
                    {doctor.specialty} • {doctor.room}
                  </p>
                </div>
              </div>

              <div className="text-right shrink-0 pl-2">
                <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-teal-100 text-teal-800 mb-0.5">
                  {doctor.waitingCount} chờ
                </span>
                <p className="text-[10px] text-slate-500 font-medium">
                  {doctor.status}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Dispatch Button */}
      <button
        type="button"
        onClick={onDispatchStaff}
        className="w-full py-2.5 px-3 bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200/80 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-colors"
      >
        <UserPlus size={15} />
        <span>Điều chuyển nhân lực ca trực</span>
      </button>
    </div>
  );
}
