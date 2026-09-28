import { Search, Filter, Users, Plus, MoreHorizontal } from 'lucide-react';
import { Specialty, Doctor } from '../../../features/appointment-booking/api';
import clsx from 'clsx';

interface SidebarProps {
  specialties: Specialty[];
  selectedSpecialtyId: string | null;
  onSelectSpecialty: (id: string) => void;
  doctors: Doctor[];
  selectedDoctorId: string | null;
  onSelectDoctor: (id: string) => void;
}

export const Sidebar = ({
  specialties,
  selectedSpecialtyId,
  onSelectSpecialty,
  doctors,
  selectedDoctorId,
  onSelectDoctor
}: SidebarProps) => {
  const selectedSpecialtyName = specialties.find(s => s.id === selectedSpecialtyId)?.name || "Khoa";

  return (
    <div className="w-full lg:w-80 flex flex-col gap-4 flex-shrink-0">
      <div className="bg-white rounded-2xl border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-slate-800">Danh Mục Chuyên Khoa</h3>
          <button className="text-sky-600 text-xs font-semibold flex items-center gap-1">
            <Filter size={12} /> Đặt lại
          </button>
        </div>
        
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input 
            type="text" 
            placeholder="Tìm theo tên BS, mã bác sĩ, phòng khám..."
            className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
          />
        </div>

        <div className="space-y-1">
          {specialties.map(spec => {
            const isActive = spec.id === selectedSpecialtyId;
            return (
              <div 
                key={spec.id} 
                onClick={() => onSelectSpecialty(spec.id)}
                className={clsx(
                  "flex items-center justify-between p-3 rounded-xl cursor-pointer",
                  isActive ? "bg-sky-50 border border-sky-100" : "hover:bg-slate-50 border border-transparent"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={clsx("w-2 h-2 mt-1.5 rounded-full", isActive ? "bg-sky-500" : "bg-slate-300")}></div>
                  <div>
                    <p className={clsx("text-sm font-bold", isActive ? "text-slate-800" : "text-slate-700")}>{spec.name}</p>
                    <p className="text-xs text-slate-500">{spec.code}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <Users size={16} className="text-sky-600" />
            Bác Sĩ Thuộc {selectedSpecialtyName}
          </h3>
          <span className="text-[10px] font-bold text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-100">{doctors.length} Đang hiển thị</span>
        </div>

        <div className="space-y-3">
          {doctors.map(doc => {
            const isActive = doc.id === selectedDoctorId;
            return (
              <div 
                key={doc.id} 
                onClick={() => onSelectDoctor(doc.id)}
                className={clsx(
                  "flex items-center gap-3 p-3 rounded-xl border relative group cursor-pointer transition-colors",
                  isActive ? "bg-sky-50 border-sky-200" : "hover:bg-slate-50 border-transparent hover:border-slate-200"
                )}
              >
                <div className="relative">
                  {doc.avatar_url ? (
                    <img src={doc.avatar_url} alt={doc.full_name} className="w-10 h-10 rounded-full border border-slate-200 shadow-sm" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-sky-100 text-sky-700 font-bold flex items-center justify-center border border-sky-200">
                      {doc.full_name.substring(0,2).toUpperCase()}
                    </div>
                  )}
                  <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-teal-500 border-2 border-white rounded-full"></div>
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-slate-800 leading-tight">{doc.title ? `${doc.title} ` : ''}{doc.full_name}</h4>
                  <div className="flex items-center gap-2 text-[10px] font-semibold mt-1">
                    <span className="text-slate-400">Mã: {doc.code}</span>
                  </div>
                </div>
                <MoreHorizontal size={16} className={clsx("text-slate-400", isActive ? "text-sky-600" : "opacity-0 group-hover:opacity-100")} />
              </div>
            );
          })}
        </div>
        
        <div className="flex gap-2 mt-4">
          <button className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-sky-50 text-sky-600 text-sm font-bold rounded-xl border border-sky-100 hover:bg-sky-100 transition-colors">
            <Plus size={16} /> Thêm Bác Sĩ
          </button>
        </div>
      </div>
    </div>
  );
};
