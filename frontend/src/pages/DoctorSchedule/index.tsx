import { schedulesCsv } from '../../features/coordinator/uiLogic';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Download, Plus, Search, Settings, X } from 'lucide-react';
import { StatCards } from './components/StatCards';
import { Sidebar } from './components/Sidebar';
import { ScheduleMatrix, WeekDay } from './components/ScheduleMatrix';
import { ActivityLog } from './components/ActivityLog';
import { DataLoadingState } from '../../components/DataLoadingState';
import { CreateScheduleModal } from './components/CreateScheduleModal';
import { ScheduleDetailModal } from './components/ScheduleDetailModal';
import {
  Doctor,
  fetchDoctorSchedules,
  fetchScheduleActivity,
  fetchDoctors,
  fetchSpecialties,
  Schedule,
  ScheduleAuditEvent,
  Specialty,
} from '../../features/appointment-booking/api';

function localIso(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfWeek(date: Date): Date {
  const result = new Date(date);
  const mondayOffset = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - mondayOffset);
  result.setHours(0, 0, 0, 0);
  return result;
}

function formatDate(date: Date): string {
  return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
}

function isoWeekNumber(date: Date): number {
  const copy = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  copy.setUTCDate(copy.getUTCDate() + 4 - (copy.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(copy.getUTCFullYear(), 0, 1));
  return Math.ceil((((copy.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

function sortSchedules(values: Schedule[]): Schedule[] {
  return [...values].sort((left, right) => new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime());
}

const CATALOG_PAGE_SIZE = 15;

export default function DoctorSchedule() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingSpecialties, setLoadingSpecialties] = useState(false);
  const [loadingMoreSpecialties, setLoadingMoreSpecialties] = useState(false);
  const [hasMoreSpecialties, setHasMoreSpecialties] = useState(false);
  const [selectedSpecialtyId, setSelectedSpecialtyId] = useState<string | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loadingDoctors, setLoadingDoctors] = useState(false);
  const [loadingMoreDoctors, setLoadingMoreDoctors] = useState(false);
  const [hasMoreDoctors, setHasMoreDoctors] = useState(false);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [activityEvents, setActivityEvents] = useState<ScheduleAuditEvent[]>([]);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<'weekly' | 'daily'>('weekly');
  const [modalDate, setModalDate] = useState<string | null>(null);
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null);
  const [activityRefreshKey, setActivityRefreshKey] = useState(0);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [loadingActivity, setLoadingActivity] = useState(false);
  const [activityError, setActivityError] = useState('');
  const [pageError, setPageError] = useState('');
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const searchTermRef = useRef(searchTerm);
  const selectedSpecialtyRef = useRef(selectedSpecialtyId);
  searchTermRef.current = searchTerm;
  selectedSpecialtyRef.current = selectedSpecialtyId;

  const weekInfo = useMemo(() => {
    const monday = startOfWeek(currentDate);
    const dayNames = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];
    const week: WeekDay[] = [];
    for (let index = 0; index < 7; index += 1) {
      const day = new Date(monday);
      day.setDate(monday.getDate() + index);
      const iso = localIso(day);
      week.push({ day: dayNames[day.getDay()], date: formatDate(day).slice(0, 5), isToday: iso === localIso(new Date()), iso });
    }
    const end = new Date(monday);
    end.setDate(monday.getDate() + 7);
    return { week, from: monday.toISOString(), to: end.toISOString(), weekNum: isoWeekNumber(monday), start: formatDate(monday), end: formatDate(new Date(end.getTime() - 86400000)) };
  }, [currentDate]);

  const selectedDoctor = doctors.find((doctor) => doctor.id === selectedDoctorId) || null;
  const visibleDays = viewMode === 'weekly' ? weekInfo.week : weekInfo.week.filter((day) => day.iso === localIso(currentDate));
  const defaultModalDate = visibleDays[0]?.iso || localIso(currentDate);

  useEffect(() => {
    let active = true;
    setLoadingSpecialties(true);
    setLoadingMoreSpecialties(false);
    setSpecialties([]);
    setHasMoreSpecialties(false);
    const timer = window.setTimeout(() => {
      fetchSpecialties({ search: searchTerm.trim(), offset: 0, limit: CATALOG_PAGE_SIZE })
        .then((data) => {
          if (!active) return;
          setSpecialties(data);
          setHasMoreSpecialties(data.length === CATALOG_PAGE_SIZE);
          setSelectedSpecialtyId((current) => current || data[0]?.id || null);
        })
        .catch(() => { if (active) setPageError('Kh\u00f4ng th\u1ec3 t\u1ea3i danh s\u00e1ch chuy\u00ean khoa.'); })
        .finally(() => { if (active) setLoadingSpecialties(false); });
    }, searchTerm ? 250 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [searchTerm]);

  useEffect(() => {
    let active = true;
    if (!selectedSpecialtyId) {
      setDoctors([]);
      setSelectedDoctorId(null);
      setHasMoreDoctors(false);
      setLoadingDoctors(false);
      return;
    }
    setDoctors([]);
    setSelectedDoctorId(null);
    setHasMoreDoctors(false);
    setLoadingDoctors(true);
    setLoadingMoreDoctors(false);
    setSchedules([]);
    setModalDate(null);
    setSelectedSchedule(null);
    setPageError('');
    const timer = window.setTimeout(() => {
      fetchDoctors({ specialtyId: searchTerm.trim() ? undefined : selectedSpecialtyId, name: searchTerm.trim() || undefined, offset: 0, limit: CATALOG_PAGE_SIZE })
        .then((data) => {
          if (!active) return;
          setDoctors(data);
          setHasMoreDoctors(data.length === CATALOG_PAGE_SIZE);
          setSelectedDoctorId(data[0]?.id || null);
        })
        .catch(() => { if (active) setPageError('Kh\u00f4ng th\u1ec3 t\u1ea3i danh s\u00e1ch b\u00e1c s\u0129.'); })
        .finally(() => { if (active) setLoadingDoctors(false); });
    }, searchTerm ? 250 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [selectedSpecialtyId, searchTerm]);

  const loadMoreSpecialties = async () => {
    const search = searchTerm.trim();
    if (!hasMoreSpecialties || loadingMoreSpecialties) return;
    setLoadingMoreSpecialties(true);
    try {
      const page = await fetchSpecialties({ search, offset: specialties.length, limit: CATALOG_PAGE_SIZE });
      if (search !== searchTermRef.current.trim()) return;
      setSpecialties((current) => [...current, ...page]);
      setHasMoreSpecialties(page.length === CATALOG_PAGE_SIZE);
    } catch {
      if (search === searchTermRef.current.trim()) setPageError('Kh\u00f4ng th\u1ec3 t\u1ea3i th\u00eam chuy\u00ean khoa.');
    } finally {
      setLoadingMoreSpecialties(false);
    }
  };

  const loadMoreDoctors = async () => {
    const search = searchTerm.trim();
    if (!selectedSpecialtyId || !hasMoreDoctors || loadingMoreDoctors) return;
    setLoadingMoreDoctors(true);
    try {
      const page = await fetchDoctors({ specialtyId: search ? undefined : selectedSpecialtyId, name: search || undefined, offset: doctors.length, limit: CATALOG_PAGE_SIZE });
      if (search !== searchTermRef.current.trim() || selectedSpecialtyId !== selectedSpecialtyRef.current) return;
      setDoctors((current) => [...current, ...page]);
      setHasMoreDoctors(page.length === CATALOG_PAGE_SIZE);
    } catch {
      if (search === searchTermRef.current.trim() && selectedSpecialtyId === selectedSpecialtyRef.current) setPageError('Kh\u00f4ng th\u1ec3 t\u1ea3i th\u00eam b\u00e1c s\u0129.');
    } finally {
      setLoadingMoreDoctors(false);
    }
  };

  useEffect(() => {
    let active = true;
    if (!selectedDoctorId) {
      setSchedules([]);
      setLoadingSchedules(false);
      return;
    }
    setSchedules([]); setModalDate(null); setSelectedSchedule(null);
    setLoadingSchedules(true);
    setPageError('');
    fetchDoctorSchedules(selectedDoctorId, weekInfo.from, weekInfo.to)
      .then((data) => { if (active) setSchedules(sortSchedules(data)); })
      .catch(() => { if (active) setPageError('Không thể tải lịch của bác sĩ trong khoảng thời gian đã chọn.'); })
      .finally(() => { if (active) setLoadingSchedules(false); });
    return () => { active = false; };
  }, [selectedDoctorId, weekInfo.from, weekInfo.to]);

  useEffect(() => {
    let active = true;
    if (!selectedDoctorId) {
      setActivityEvents([]);
      setLoadingActivity(false);
      return;
    }
    setActivityEvents([]);
    setLoadingActivity(true);
    setActivityError('');
    fetchScheduleActivity(selectedDoctorId, weekInfo.from, weekInfo.to)
      .then((data) => { if (active) setActivityEvents(data); })
      .catch(() => { if (active) setActivityError('Không thể tải nhật ký thao tác của bác sĩ.'); })
      .finally(() => { if (active) setLoadingActivity(false); });
    return () => { active = false; };
  }, [selectedDoctorId, weekInfo.from, weekInfo.to, activityRefreshKey]);

  const moveDate = (days: number) => setCurrentDate((date) => {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
  });

  const selectSpecialty = (id: string) => {
    setSelectedSpecialtyId(id);
    if (searchTerm) setSearchTerm('');
  };

  const handleCreated = (schedule: Schedule) => {
    if (schedule.doctor_id !== selectedDoctorId || new Date(schedule.starts_at).getTime() < new Date(weekInfo.from).getTime() || new Date(schedule.starts_at).getTime() >= new Date(weekInfo.to).getTime()) return;
    setSchedules((current) => sortSchedules([...current, schedule]));
    setModalDate(null);
    setActivityRefreshKey((value) => value + 1);
    setNotice({ type: 'success', message: 'Đã tạo lịch khám thành công.' });
  };

  const handleUpdated = (schedule: Schedule) => {
    if (schedule.doctor_id !== selectedDoctorId) return;
    setSchedules((current) => sortSchedules(current.map((item) => item.id === schedule.id ? schedule : item)));
    setSelectedSchedule(null);
    setActivityRefreshKey((value) => value + 1);
    setNotice({ type: 'success', message: 'Đã cập nhật lịch khám thành công.' });
  };

  const exportSchedules = () => {
    const url = URL.createObjectURL(new Blob(['\uFEFF' + schedulesCsv(schedules, selectedDoctor?.full_name || '')], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'lich-bac-si-' + localIso(currentDate) + '.csv'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <div className="doctor-schedule-page flex h-[calc(100dvh-4rem)] min-h-0 flex-col bg-[#f4f8f5] font-sans">
      <div className="schedule-scrollbar min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-7">
        <div className="mx-auto w-full max-w-[1900px]">
        <div className="mb-6 flex flex-col justify-between gap-5 rounded-3xl border border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/80 p-5 shadow-sm sm:p-7 xl:flex-row xl:items-center">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">Quản lý & đăng ký lịch khám bác sĩ</h2>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-emerald-800"><Settings size={12} /> Quản lý lịch theo thời gian thực</span>
            </div>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Chọn chuyên khoa, bác sĩ và theo dõi từng mốc giờ có thể nhận bệnh nhân.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => selectedDoctor && setModalDate(defaultModalDate)} disabled={!selectedDoctor} className="flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-bold text-white shadow-md shadow-emerald-900/10 transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"><Plus size={18} /> Thêm lịch khám</button>

            <button disabled={loadingSchedules || !schedules.length} onClick={exportSchedules} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50 disabled:opacity-50"><Download size={18} /> Xuất báo cáo</button>
          </div>
        </div>

        <div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4 xl:flex-row xl:items-center">
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => moveDate(viewMode === 'weekly' ? -7 : -1)} className="rounded-lg p-2 text-slate-500 hover:bg-emerald-50 hover:text-emerald-700"><ChevronLeft size={20} /></button>
            <div className="flex items-center gap-2 px-2 py-1.5 text-sm font-bold text-slate-800"><Calendar size={18} className="text-emerald-700" /> Tuần {weekInfo.weekNum}: {weekInfo.start} — {weekInfo.end}</div>
            <button onClick={() => moveDate(viewMode === 'weekly' ? 7 : 1)} className="rounded-lg p-2 text-slate-500 hover:bg-emerald-50 hover:text-emerald-700"><ChevronRight size={20} /></button>
            <button onClick={() => setCurrentDate(new Date())} className="rounded-xl bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-800 hover:bg-emerald-100">Hôm nay</button>
          </div>
          <div className="flex flex-wrap items-center gap-4 pr-4">
            <div className="flex rounded-xl bg-slate-100 p-1">
              <button onClick={() => setViewMode('weekly')} aria-pressed={viewMode === 'weekly'} className={`rounded-lg px-4 py-2 text-sm font-bold ${viewMode === 'weekly' ? 'bg-white text-emerald-800 shadow-sm' : 'text-slate-500'}`}>Theo tuần</button>
              <button onClick={() => setViewMode('daily')} aria-pressed={viewMode === 'daily'} className={`rounded-lg px-4 py-2 text-sm font-bold ${viewMode === 'daily' ? 'bg-white text-emerald-800 shadow-sm' : 'text-slate-500'}`}>Theo ngày</button>
            </div>
            <div className="flex items-center gap-3 text-xs font-semibold text-slate-600"><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Còn lượt</span><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> Đã kín/khóa</span></div>
          </div>
        </div>

        <section aria-label="Tìm kiếm" className="mb-6 rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm sm:p-5">
          <label htmlFor="doctor-schedule-search" className="mb-2 block text-sm font-bold text-slate-800">Tìm bác sĩ hoặc chuyên khoa</label>
          <span className="relative block">
            <Search aria-hidden="true" size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input id="doctor-schedule-search" type="search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Nhập tên bác sĩ, mã hoặc chuyên khoa" className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3.5 pl-11 pr-11 text-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" />
            {searchTerm && <button type="button" onClick={() => setSearchTerm('')} aria-label="Xóa tìm kiếm" className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-slate-700"><X size={16} /></button>}
          </span>
          <p className="mt-2 text-xs text-slate-500">Kết quả chuyên khoa và bác sĩ được lọc đồng thời.</p>
        </section>

        <StatCards schedules={schedules} loading={loadingSchedules} />
        {pageError && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{pageError}</div>}
        {notice && <div className={`mb-4 rounded-xl border px-4 py-3 text-sm ${notice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`} role="status">{notice.message}</div>}

        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[21rem_minmax(0,1fr)]">
          <Sidebar specialties={specialties} selectedSpecialtyId={selectedSpecialtyId} onSelectSpecialty={selectSpecialty} doctors={doctors} selectedDoctorId={selectedDoctorId} onSelectDoctor={setSelectedDoctorId} doctorSearch={searchTerm} loadingSpecialties={loadingSpecialties} loadingMoreSpecialties={loadingMoreSpecialties} hasMoreSpecialties={hasMoreSpecialties} onLoadMoreSpecialties={loadMoreSpecialties} loadingDoctors={loadingDoctors} loadingMoreDoctors={loadingMoreDoctors} hasMoreDoctors={hasMoreDoctors} onLoadMoreDoctors={loadMoreDoctors} />
          <div className="min-w-0 flex flex-col gap-4">
            {loadingSchedules && <DataLoadingState className="py-8 flex flex-col items-center justify-center text-slate-400" label="Đang tải lịch bác sĩ…" />}
            <ScheduleMatrix doctor={selectedDoctor} schedules={schedules} weekDays={visibleDays} onAddSchedule={setModalDate} onScheduleClick={setSelectedSchedule} />
            <ActivityLog doctor={selectedDoctor} schedules={schedules} events={activityEvents} loading={loadingActivity} error={activityError} />
          </div>
        </div>
        </div>
      </div>
      {modalDate && selectedDoctor && <CreateScheduleModal doctor={selectedDoctor} defaultDate={modalDate} onClose={() => setModalDate(null)} onCreated={handleCreated} />}
      {selectedSchedule && selectedDoctor && <ScheduleDetailModal doctor={selectedDoctor} schedule={selectedSchedule} onClose={() => setSelectedSchedule(null)} onUpdated={handleUpdated} />}
    </div>
  );
}
