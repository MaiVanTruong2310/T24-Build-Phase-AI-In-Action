import { Sparkles, Check, ShieldCheck, User } from 'lucide-react';
import clsx from 'clsx';
import { Doctor } from '../api';

interface Props {
  doctors: Doctor[];
  selectedDoctorId: string;
  onSelectDoctor: (id: string) => void;
}

export function DoctorCard({ doctors, selectedDoctorId, onSelectDoctor }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-slate-900 flex items-center gap-2">
          2. Bác Sĩ Chuyên Trách
        </h2>
        <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">Đang Phụ Trách</span>
      </div>

      <div className="bg-white rounded-2xl border border-sky-100 shadow-sm overflow-hidden relative">
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-sky-400 to-emerald-400"></div>
        <div className="p-4">
          <div className="inline-flex items-center gap-1.5 bg-sky-50 text-sky-700 text-xs font-semibold px-2.5 py-1 rounded-md mb-4">
            <Sparkles className="w-3.5 h-3.5" /> AI đề xuất dựa trên triệu chứng tức ngực
          </div>

          {doctors.length === 0 && <p className="text-sm text-slate-500 py-2">Đang tải danh sách bác sĩ...</p>}

          <div className="space-y-4">
            {doctors.map(doctor => {
              const isSelected = doctor.id === selectedDoctorId;
              return (
                <div
                  key={doctor.id}
                  className={clsx(
                    "relative rounded-xl border p-3 cursor-pointer transition-all",
                    isSelected ? "border-emerald-500 bg-emerald-50/30 ring-1 ring-emerald-500" : "border-slate-100 hover:border-emerald-200"
                  )}
                  onClick={() => onSelectDoctor(doctor.id)}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center text-white shadow-sm">
                      <Check className="w-3 h-3" />
                    </div>
                  )}
                  <div className="flex gap-4">
                    <div className="relative shrink-0">
                      {doctor.avatar_url ? (
                        <img src={doctor.avatar_url} alt="Doctor" className="w-14 h-14 rounded-xl object-cover border border-slate-200" />
                      ) : (
                        <div className="w-14 h-14 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
                          <User className="w-6 h-6" />
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-sm">{doctor.title} {doctor.full_name}</div>
                      <div className="text-sky-600 text-xs font-medium mb-1.5">{doctor.code}</div>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500">
                        <div className="flex items-center gap-1">
                          <span className="text-amber-500 font-bold">★ {doctor.rating || '4.9'}</span>
                        </div>
                        <div className="w-1 h-1 rounded-full bg-slate-300"></div>
                        <div>{doctor.experience_years || 15} năm kinh nghiệm</div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 bg-slate-50 rounded-xl p-3 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Phí khám chuyên khoa</div>
                      <div className="font-bold text-sky-700 text-lg">
                        {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(doctor.price || 350000)}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded">
                      <ShieldCheck className="w-3.5 h-3.5" /> BHYT hỗ trợ 80%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
