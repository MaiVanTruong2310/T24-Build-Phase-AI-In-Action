import { schedulesCsv } from '../../features/coordinator/uiLogic';
import { useEffect, useMemo, useState } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Download, Plus, Settings, ShieldAlert } from 'lucide-react';
import { StatCards } from './components/StatCards';
import { Sidebar } from './components/Sidebar';
import { ScheduleMatrix, WeekDay } from './components/ScheduleMatrix';
import { ActivityLog } from './components/ActivityLog';
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

export default function DoctorSchedule() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialtyId, setSelectedSpecialtyId] = useState<string | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
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
    fetchSpecialties()
      .then((data) => {
        if (!active) return;
        setSpecialties(data);
        setSelectedSpecialtyId(data[0]?.id || null);
      })
      .catch(() => { if (active) setPageError('Không thể tải danh sách chuyên khoa.'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    if (!selectedSpecialtyId) {
      setDoctors([]);
      setSelectedDoctorId(null);
      return;
    }
    setDoctors([]);
    setSelectedDoctorId(null);
    fetchDoctors(selectedSpecialtyId)
      .then((data) => {
        if (!active) return;
        setDoctors(data);
        setSelectedDoctorId(data[0]?.id || null);
      })
      .catch(() => { if (active) setPageError('Không thể tải danh sách bác sĩ.'); });
    return () => { active = false; };
  }, [selectedSpecialtyId]);

  useEffect(() => {
    let active = true;
    if (!selectedDoctorId) {
      setSchedules([]);
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
    <div className="flex h-full flex-col bg-slate-50 font-sans">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-extrabold text-slate-800">Quản lý & đăng ký lịch khám bác sĩ</h2>
              <span className="flex items-center gap-1 rounded bg-sky-100 px-2 py-0.5 text-[11px] font-bold text-sky-700"><Settings size={12} /> Quản lý lịch theo thời gian thực</span>
            </div>
            <p className="text-sm text-slate-500">Chọn chuyên khoa, bác sĩ và theo dõi từng mốc giờ có thể nhận bệnh nhân.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => selectedDoctor && setModalDate(defaultModalDate)} disabled={!selectedDoctor} className="flex items-center gap-2 rounded-xl bg-sky-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"><Plus size={18} /> Thêm lịch khám</button>

            <button disabled={loadingSchedules || !schedules.length} onClick={exportSchedules} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"><Download size={18} /> Xuất báo cáo</button>
          </div>
        </div>

        <div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm xl:flex-row xl:items-center">
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => moveDate(viewMode === 'weekly' ? -7 : -1)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600"><ChevronLeft size={20} /></button>
            <div className="flex items-center gap-2 px-3 py-1.5 text-sm font-bold text-slate-800"><Calendar size={18} className="text-sky-600" /> Tuần {weekInfo.weekNum}: {weekInfo.start} — {weekInfo.end}</div>
            <button onClick={() => moveDate(viewMode === 'weekly' ? 7 : 1)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600"><ChevronRight size={20} /></button>
            <button onClick={() => setCurrentDate(new Date())} className="rounded-xl bg-slate-100 px-4 py-1.5 text-sm font-bold text-slate-700 hover:bg-slate-200">Hôm nay</button>
          </div>
          <div className="flex flex-wrap items-center gap-4 pr-4">
            <div className="flex rounded-xl bg-slate-100 p-1">
              <button onClick={() => setViewMode('weekly')} className={`rounded-lg px-4 py-1.5 text-sm font-bold ${viewMode === 'weekly' ? 'bg-white text-sky-700 shadow-sm' : 'text-slate-500'}`}>Theo tuần</button>
              <button onClick={() => setViewMode('daily')} className={`rounded-lg px-4 py-1.5 text-sm font-bold ${viewMode === 'daily' ? 'bg-white text-sky-700 shadow-sm' : 'text-slate-500'}`}>Theo ngày</button>
            </div>
            <div className="flex items-center gap-3 text-xs font-semibold text-slate-600"><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Còn lượt</span><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> Đã kín/khóa</span></div>
          </div>
        </div>

        <StatCards schedules={schedules} loading={loadingSchedules} />
        {pageError && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{pageError}</div>}
        {notice && <div className={`mb-4 rounded-xl border px-4 py-3 text-sm ${notice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`} role="status">{notice.message}</div>}

        <div className="flex flex-col gap-6 lg:flex-row">
          <Sidebar specialties={specialties} selectedSpecialtyId={selectedSpecialtyId} onSelectSpecialty={setSelectedSpecialtyId} doctors={doctors} selectedDoctorId={selectedDoctorId} onSelectDoctor={setSelectedDoctorId} />
          <div className="flex flex-1 flex-col gap-4">
            {loadingSchedules && <div className="rounded-xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-700">Đang tải lịch bác sĩ...</div>}
            <ScheduleMatrix doctor={selectedDoctor} schedules={schedules} weekDays={visibleDays} onAddSchedule={setModalDate} onScheduleClick={setSelectedSchedule} />
            <ActivityLog doctor={selectedDoctor} schedules={schedules} events={activityEvents} loading={loadingActivity} error={activityError} />
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-4 text-xs text-slate-500"><span className="flex items-center gap-2"><ShieldAlert size={14} /> Lịch tạo mới được kiểm tra conflict ở backend trước khi lưu.</span><span>Audit lịch khám</span></div>
      {modalDate && selectedDoctor && <CreateScheduleModal doctor={selectedDoctor} defaultDate={modalDate} onClose={() => setModalDate(null)} onCreated={handleCreated} />}
      {selectedSchedule && selectedDoctor && <ScheduleDetailModal doctor={selectedDoctor} schedule={selectedSchedule} onClose={() => setSelectedSchedule(null)} onUpdated={handleUpdated} />}
    </div>
  );
}
