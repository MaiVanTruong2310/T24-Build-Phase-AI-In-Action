import { Check, Loader2, User } from 'lucide-react';
import clsx from 'clsx';
import { Doctor } from '../api';

interface Props {
  doctors: Doctor[];
  selectedDoctorId: string;
  onSelectDoctor: (id: string) => void;
  loading?: boolean;
}

export function DoctorCard({ doctors, selectedDoctorId, onSelectDoctor, loading = false }: Props) {
  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-bold text-slate-900">3. Bác sĩ</h2>
        <span className="text-xs font-medium text-slate-500">Chọn một bác sĩ</span>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="p-4">
          {loading && (
            <div className="flex items-center gap-2 py-3 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin text-sky-600" /> Đang tải bác sĩ phù hợp...
            </div>
          )}
          {!loading && doctors.length === 0 && (
            <p className="rounded-xl bg-slate-50 px-4 py-5 text-sm leading-6 text-slate-500">
              Chưa có bác sĩ và lịch làm việc phù hợp với chuyên khoa, cơ sở và dịch vụ đã chọn.
            </p>
          )}

          <div className="space-y-3">
            {doctors.map((doctor) => {
              const isSelected = doctor.id === selectedDoctorId;
              const facilityNames = doctor.facilities
                ?.map((item) => item.facility?.name)
                .filter((name): name is string => Boolean(name))
                .join(', ');
              return (
                <button
                  type="button"
                  key={doctor.id}
                  onClick={() => onSelectDoctor(doctor.id)}
                  className={clsx(
                    'relative w-full rounded-xl border p-3 text-left transition-all',
                    isSelected ? 'border-emerald-500 bg-emerald-50/40 ring-1 ring-emerald-500' : 'border-slate-200 hover:border-emerald-300',
                  )}
                >
                  {isSelected && (
                    <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white">
                      <Check className="h-3 w-3" />
                    </span>
                  )}
                  <span className="flex gap-3">
                    <span className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-slate-100 text-slate-400">
                      {doctor.avatar_url ? <img src={doctor.avatar_url} alt={doctor.full_name} className="h-full w-full object-cover" /> : <User className="h-6 w-6" />}
                    </span>
                    <span className="min-w-0 pr-6">
                      <span className="block truncate text-sm font-bold text-slate-900">{[doctor.title, doctor.full_name].filter(Boolean).join(' ')}</span>
                      <span className="mt-1 block text-xs text-slate-500">Mã bác sĩ: {doctor.code}</span>
                      {doctor.bio && <span className="mt-2 line-clamp-2 block text-xs leading-5 text-slate-600">{doctor.bio}</span>}
                    </span>
                  </span>
                  {facilityNames && <span className="mt-3 block border-t border-slate-100 pt-3 text-xs text-slate-500">Cơ sở phụ trách: {facilityNames}</span>}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
