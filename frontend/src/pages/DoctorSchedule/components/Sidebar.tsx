import { Plus, Stethoscope } from 'lucide-react';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import type { Doctor, Specialty } from '../../../features/appointment-booking/api';
import { filterDoctors } from '../filterDoctors';

interface SidebarProps {
  specialties: Specialty[];
  selectedSpecialtyId: string | null;
  onSelectSpecialty: (id: string) => void;
  doctors: Doctor[];
  selectedDoctorId: string | null;
  onSelectDoctor: (id: string) => void;
  doctorSearch: string;
  loadingSpecialties: boolean;
  loadingMoreSpecialties: boolean;
  hasMoreSpecialties: boolean;
  onLoadMoreSpecialties: () => void;
  loadingDoctors: boolean;
  loadingMoreDoctors: boolean;
  hasMoreDoctors: boolean;
  onLoadMoreDoctors: () => void;
}

export const Sidebar = ({ specialties, selectedSpecialtyId, onSelectSpecialty, doctors, selectedDoctorId, onSelectDoctor, doctorSearch, loadingSpecialties, loadingMoreSpecialties, hasMoreSpecialties, onLoadMoreSpecialties, loadingDoctors, loadingMoreDoctors, hasMoreDoctors, onLoadMoreDoctors }: SidebarProps) => {
  const visibleDoctors = useMemo(() => filterDoctors(doctors, doctorSearch), [doctors, doctorSearch]);
  const selectedSpecialtyName = doctorSearch ? 'Kết quả tìm kiếm' : specialties.find((item) => item.id === selectedSpecialtyId)?.name || 'Chuyên khoa';

  return (
    <aside className="flex min-w-0 flex-col gap-4">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 bg-gradient-to-r from-emerald-50 to-white px-5 py-4">
          <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-emerald-800">Bước 1</p>
          <h3 className="mt-1 text-base font-bold text-slate-900">Chuyên khoa</h3>
          <p className="mt-1 text-xs text-slate-500">Chọn khoa để lọc danh sách bác sĩ</p>
        </div>
        <div className="p-3">
          <div className="space-y-1">
            {specialties.map((specialty) => {
              const active = specialty.id === selectedSpecialtyId;
              return <button key={specialty.id} type="button" onClick={() => onSelectSpecialty(specialty.id)} aria-pressed={active} title={specialty.name}
                className={clsx('flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700', active ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : 'border-transparent text-slate-700 hover:bg-slate-50')}>
                <span className={clsx('h-2.5 w-2.5 shrink-0 rounded-full', active ? 'bg-emerald-600 ring-4 ring-emerald-100' : 'bg-slate-300')} />
                <span className="line-clamp-2 min-w-0 flex-1 text-sm font-semibold">{specialty.name}</span>
              </button>;
            })}
            {!loadingSpecialties && specialties.length === 0 && <p className="rounded-xl bg-slate-50 px-3 py-5 text-center text-sm text-slate-500">Không tìm thấy chuyên khoa.</p>}
            {loadingSpecialties && specialties.length === 0 && <p className="px-3 py-4 text-center text-sm text-slate-500">Đang tải chuyên khoa…</p>}
          </div>
          {hasMoreSpecialties && <button type="button" onClick={onLoadMoreSpecialties} disabled={loadingMoreSpecialties} className="mt-2 w-full rounded-lg py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700">
            {loadingMoreSpecialties ? 'Đang tải…' : 'Xem thêm chuyên khoa'}
          </button>}
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-emerald-800">Bước 2</p>
            <h3 className="mt-1 flex items-center gap-2 text-base font-bold text-slate-900"><Stethoscope size={17} className="shrink-0 text-emerald-700" /><span className="truncate">Bác sĩ · {selectedSpecialtyName}</span></h3>
          </div>
          <span title="Số bác sĩ đã tải" className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{visibleDoctors.length} đã tải</span>
        </div>
        <div className="space-y-2">
          {visibleDoctors.map((doctor) => {
            const active = doctor.id === selectedDoctorId;
            return <button key={doctor.id} type="button" onClick={() => onSelectDoctor(doctor.id)} aria-pressed={active}
              className={clsx('flex w-full items-center gap-3 rounded-xl border p-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700', active ? 'border-emerald-200 bg-emerald-50' : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50')}>
              {doctor.avatar_url ? <img src={doctor.avatar_url} alt="" className="h-10 w-10 shrink-0 rounded-full border border-slate-200 object-cover" /> : <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-emerald-100 bg-emerald-50 text-sm font-bold text-emerald-800">{doctor.full_name.slice(0, 2).toUpperCase()}</span>}
              <span className="min-w-0 flex-1">
                <span title={`${doctor.title ? `${doctor.title} ` : ''}${doctor.full_name}`} className="line-clamp-2 block text-sm font-bold leading-5 text-slate-800">{doctor.title ? `${doctor.title} ` : ''}{doctor.full_name}</span>
                <span className="mt-1 block truncate text-xs text-slate-500">Mã: {doctor.code}</span>
              </span>
              <span className={clsx('h-2 w-2 shrink-0 rounded-full', active ? 'bg-emerald-600' : 'bg-slate-200')} />
            </button>;
          })}
          {!loadingDoctors && !loadingMoreDoctors && visibleDoctors.length === 0 && <p className="rounded-xl bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">Không tìm thấy bác sĩ phù hợp.</p>}
          {(loadingDoctors || loadingMoreDoctors) && <p className="px-3 py-3 text-center text-sm text-slate-500">Đang tải bác sĩ…</p>}
        </div>
        {hasMoreDoctors && <button type="button" onClick={onLoadMoreDoctors} disabled={loadingMoreDoctors || loadingDoctors} className="mt-2 w-full rounded-lg py-2 text-sm font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700">
          {loadingMoreDoctors ? 'Đang tải…' : 'Xem thêm bác sĩ'}
        </button>}
        <Link to="/staff/doctors/create" className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-emerald-200 bg-emerald-50/60 py-3 text-sm font-bold text-emerald-800 transition hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700">
          <Plus size={16} /> Thêm bác sĩ
        </Link>
      </section>
    </aside>
  );
};
