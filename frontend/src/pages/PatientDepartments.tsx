import { useEffect, useState } from 'react';
import { Search, Stethoscope } from 'lucide-react';
import { fetchDoctors, fetchFacilities, fetchSpecialties, Doctor, Facility, Specialty } from '../features/appointment-booking/api';

export default function PatientDepartments() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [specialtyId, setSpecialtyId] = useState('');
  const [facilityId, setFacilityId] = useState('');
  const [name, setName] = useState('');
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [doctorsLoading, setDoctorsLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [doctorError, setDoctorError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([fetchSpecialties(), fetchFacilities()])
      .then(([loadedSpecialties, loadedFacilities]) => {
        if (!active) return;
        setSpecialties(loadedSpecialties);
        setFacilities(loadedFacilities);
      })
      .catch((reason: unknown) => {
        if (active) setCatalogError(reason instanceof Error ? reason.message : 'Không thể tải danh mục.');
      })
      .finally(() => { if (active) setCatalogLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setDoctorsLoading(true);
    setDoctorError('');
    fetchDoctors({ specialtyId: specialtyId || undefined, facilityId: facilityId || undefined, name: name.trim() || undefined })
      .then((items) => { if (active) setDoctors(items); })
      .catch((reason: unknown) => {
        if (!active) return;
        setDoctors([]);
        setDoctorError(reason instanceof Error ? reason.message : 'Không thể tải danh sách bác sĩ.');
      })
      .finally(() => { if (active) setDoctorsLoading(false); });
    return () => { active = false; };
  }, [specialtyId, facilityId, name]);

  return (
    <section className="mx-auto max-w-6xl rounded-2xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface p-6 shadow-sm md:p-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-sky-100 light:bg-app-tint p-3 text-sky-700 light:text-app-primary"><Stethoscope className="h-6 w-6" /></div>
        <div><p className="text-xs font-semibold uppercase tracking-wider text-sky-600 light:text-app-primary">Tra cứu y tế</p><h1 className="text-2xl font-bold text-slate-900 light:text-app-text">Tìm khoa và bác sĩ</h1></div>
      </div>
      <div className="mb-6 grid gap-3 rounded-xl bg-slate-50 light:bg-app-page p-4 md:grid-cols-3">
        <label className="text-sm font-semibold text-slate-700 light:text-app-text">Tên bác sĩ<input className="mt-1.5 w-full rounded-lg border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2 font-normal" placeholder="Tìm theo tên" value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="text-sm font-semibold text-slate-700 light:text-app-text">Chuyên khoa<select className="mt-1.5 w-full rounded-lg border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2 font-normal" value={specialtyId} onChange={(event) => setSpecialtyId(event.target.value)}><option value="">Tất cả chuyên khoa</option>{specialties.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="text-sm font-semibold text-slate-700 light:text-app-text">Cơ sở<select className="mt-1.5 w-full rounded-lg border border-slate-200 light:border-app-border bg-white light:bg-app-surface px-3 py-2 font-normal" value={facilityId} onChange={(event) => setFacilityId(event.target.value)}><option value="">Tất cả cơ sở</option>{facilities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </div>
      {(catalogError || doctorError) && <div role="alert" className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">{catalogError || doctorError}</div>}
      {catalogLoading || doctorsLoading ? <p role="status" className="text-sm text-slate-500 light:text-app-secondary">Đang tải catalog...</p> : doctors.length === 0 ? <p className="rounded-xl border border-dashed border-slate-200 light:border-app-border p-8 text-center text-sm text-slate-500 light:text-app-secondary">Không tìm thấy bác sĩ phù hợp.</p> : <div className="grid gap-4 md:grid-cols-2">{doctors.map((doctor) => <article className="rounded-xl border border-slate-200 light:border-app-border p-4" key={doctor.id}><div className="flex gap-3"><div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-xl bg-sky-50 light:bg-app-muted text-sky-700 light:text-app-primary">{doctor.avatar_url ? <img alt={doctor.full_name} className="h-full w-full object-cover" src={doctor.avatar_url} /> : <Search className="h-5 w-5" />}</div><div><h2 className="font-bold text-slate-900 light:text-app-text">{doctor.title ? `${doctor.title} ` : ''}{doctor.full_name}</h2><p className="text-sm text-slate-500 light:text-app-secondary">{doctor.code}</p></div></div><p className="mt-3 text-sm text-slate-600 light:text-app-secondary">{doctor.specialties?.map((item) => item.name).join(', ') || 'Chưa cập nhật chuyên khoa'}</p><p className="mt-1 text-sm text-slate-500 light:text-app-secondary">{doctor.facilities?.map((item) => item.facility?.name).filter(Boolean).join(', ') || 'Chưa cập nhật cơ sở'}</p></article>)}</div>}
    </section>
  );
}
