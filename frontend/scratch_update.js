const fs = require('fs');
const path = require('path');

const apiPath = path.join('c:/Project/Vin/Build_Phase/P-124/frontend/src/features/appointment-booking/api.ts');
const indexFile = path.join('c:/Project/Vin/Build_Phase/P-124/frontend/src/pages/DoctorSchedule/index.tsx');
const sidebarFile = path.join('c:/Project/Vin/Build_Phase/P-124/frontend/src/pages/DoctorSchedule/components/Sidebar.tsx');
const matrixFile = path.join('c:/Project/Vin/Build_Phase/P-124/frontend/src/pages/DoctorSchedule/components/ScheduleMatrix.tsx');

const indexCode = import React, { useState, useEffect } from 'react';
import {
  Settings, Plus, Calendar, Download, Zap, ShieldAlert,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import { TopNav } from './components/TopNav';
import { StatCards } from './components/StatCards';
import { Sidebar } from './components/Sidebar';
import { ScheduleMatrix } from './components/ScheduleMatrix';
import { ActivityLog } from './components/ActivityLog';
import { fetchSpecialties, fetchDoctors, fetchAvailability, Specialty, Doctor, Schedule } from '../../features/appointment-booking/api';

export default function DoctorSchedule() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialtyId, setSelectedSpecialtyId] = useState<string | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);
  const [schedules, setSchedules] = useState<Schedule[]>([]);

  useEffect(() => {
    fetchSpecialties().then(data => {
      setSpecialties(data);
      if (data.length > 0) setSelectedSpecialtyId(data[0].id);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedSpecialtyId) return;
    setDoctors([]);
    setSelectedDoctorId(null);
    fetchDoctors(selectedSpecialtyId).then(data => {
      setDoctors(data);
      if (data.length > 0) setSelectedDoctorId(data[0].id);
    }).catch(console.error);
  }, [selectedSpecialtyId]);

  useEffect(() => {
    if (!selectedDoctorId) {
      setSchedules([]);
      return;
    }
    const dates = ['2024-10-21', '2024-10-22', '2024-10-23', '2024-10-24', '2024-10-25', '2024-10-26', '2024-10-27'];
    Promise.all(dates.map(d => fetchAvailability(selectedDoctorId, d)))
      .then(results => {
        setSchedules(results.flat());
      })
      .catch(console.error);
  }, [selectedDoctorId]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <TopNav />
      
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-extrabold text-slate-800">Quản Lý & Đăng Ký Lịch Khám Bác Sĩ</h2>
              <span className="px-2 py-0.5 bg-sky-100 text-sky-700 text-[11px] font-bold flex items-center gap-1 rounded">
                <Settings size={12} /> Hệ thống phân bổ công suất khám y tế tự động v4.2
              </span>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[11px] font-bold rounded-full">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block mr-1"></div>
                Phòng Khám Đang Mở Cửa (Ca Ngày)
              </span>
            </div>
            <p className="text-sm text-slate-500">Phân bổ chỉ tiêu bệnh nhân, ca trực lâm sàng và kiểm soát công suất phòng khám theo thời gian thực.</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button className="px-4 py-2.5 bg-sky-700 text-white text-sm font-bold rounded-xl flex items-center gap-2 hover:bg-sky-800 transition-colors shadow-sm">
              <Plus size={18} /> Đăng Ký / Thêm Lịch Khám Mới
            </button>
            <button className="px-4 py-2.5 bg-white text-teal-600 text-sm font-bold rounded-xl flex items-center gap-2 border border-teal-200 hover:bg-teal-50 transition-colors shadow-sm">
              <Zap size={18} /> Phân Bổ Lịch Tự Động Bằng AI
            </button>
            <button className="px-4 py-2.5 bg-white text-slate-700 text-sm font-bold rounded-xl flex items-center gap-2 border border-slate-200 hover:bg-slate-50 transition-colors shadow-sm">
              <Download size={18} /> Xuất Báo Cáo
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between mb-6 bg-white p-2 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2">
            <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg"><ChevronLeft size={20} /></button>
            <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-bold text-slate-800 hover:bg-slate-50 rounded-lg">
              <Calendar size={18} className="text-sky-600" /> Tuần 42: 21/10/2024 — 27/10/2024
            </button>
            <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg"><ChevronRight size={20} /></button>
            
            <div className="w-px h-6 bg-slate-200 mx-2"></div>
            
            <button className="px-4 py-1.5 bg-slate-100 text-slate-700 text-sm font-bold rounded-xl hover:bg-slate-200 transition-colors">
              Hôm nay (22/10)
            </button>
          </div>

          <div className="flex items-center gap-6 pr-4">
            <div className="flex bg-slate-100 p-1 rounded-xl">
              <button className="px-4 py-1.5 bg-white text-sky-700 text-sm font-bold rounded-lg shadow-sm">
                Theo Tuần (Weekly Matrix)
              </button>
              <button className="px-4 py-1.5 text-slate-500 text-sm font-semibold rounded-lg hover:text-slate-700">
                Theo Ngày (Daily Slots)
              </button>
            </div>
            
            <div className="w-px h-6 bg-slate-200"></div>
            
            <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-emerald-500 rounded-full"></div> Còn trống</span>
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-sky-400 rounded-full"></div> Đang nhận</span>
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-rose-500 rounded-full"></div> Kín 100%</span>
            </div>
          </div>
        </div>

        <StatCards />

        <div className="flex gap-6">
          <Sidebar 
            specialties={specialties}
            selectedSpecialtyId={selectedSpecialtyId}
            onSelectSpecialty={setSelectedSpecialtyId}
            doctors={doctors}
            selectedDoctorId={selectedDoctorId}
            onSelectDoctor={setSelectedDoctorId}
          />
          <div className="flex-1 flex flex-col">
            <ScheduleMatrix 
              doctor={doctors.find(d => d.id === selectedDoctorId) || null}
              schedules={schedules}
            />
            <ActivityLog />
          </div>
        </div>
      </div>
      
      <div className="px-6 py-4 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <ShieldAlert size={14} className="text-slate-400" />
          <span>MediCare AI Clinical HITL Management System - Chuẩn HIPAA & Bộ Y Tế. Hệ thống tự động ghi nhật ký can thiệp y khoa.</span>
        </div>
        <div className="flex gap-4 font-medium">
          <span>Audit ID: MC-HITL-2024-SYS</span>
          <span className="text-teal-600 font-bold">Phiên trực: Phòng Trực Cấp Cứu 01</span>
        </div>
      </div>
    </div>
  );
}
;

const sidebarCode = import { Search, Filter, Users, Plus, Settings, Activity, ArrowRight, MoreHorizontal } from 'lucide-react';
import { Specialty, Doctor } from '../../../../features/appointment-booking/api';
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
    <div className="w-80 flex flex-col gap-4 flex-shrink-0">
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
                  <h4 className="text-sm font-bold text-slate-800 leading-tight">{doc.title ? \\ \ : ''}{doc.full_name}</h4>
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
;

const matrixCode = import { Plus, Settings, ShieldAlert } from 'lucide-react';
import { Schedule, Doctor } from '../../../../features/appointment-booking/api';
import clsx from 'clsx';

interface ScheduleMatrixProps {
  doctor: Doctor | null;
  schedules: Schedule[];
}

export const ScheduleMatrix = ({ doctor, schedules }: ScheduleMatrixProps) => {
  const dates = [
    { day: 'Thứ Hai', date: '21/10', isToday: false, iso: '2024-10-21' },
    { day: 'Thứ Ba (Nay)', date: '22/10', isToday: true, iso: '2024-10-22' },
    { day: 'Thứ Tư', date: '23/10', isToday: false, iso: '2024-10-23' },
    { day: 'Thứ Năm', date: '24/10', isToday: false, iso: '2024-10-24' },
    { day: 'Thứ Sáu', date: '25/10', isToday: false, iso: '2024-10-25' },
    { day: 'Thứ Bảy', date: '26/10', isToday: false, iso: '2024-10-26' },
    { day: 'Chủ Nhật', date: '27/10', isToday: false, iso: '2024-10-27' },
  ];

  return (
    <div className="flex-1 bg-white rounded-2xl border border-slate-200 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-500 mr-2">Bộ lọc ca khám:</span>
          <button className="px-4 py-1.5 bg-sky-700 text-white text-sm font-bold rounded-full shadow-sm">Tất cả các ca</button>
          <button className="px-4 py-1.5 bg-slate-100 text-slate-600 hover:bg-slate-200 text-sm font-semibold rounded-full transition-colors">Ca Sáng</button>
          <button className="px-4 py-1.5 bg-slate-100 text-slate-600 hover:bg-slate-200 text-sm font-semibold rounded-full transition-colors">Ca Chiều</button>
        </div>
      </div>

      <div className="grid grid-cols-[1.5fr_repeat(7,1fr)] border-b border-slate-200 bg-slate-50">
        <div className="p-4 text-xs font-bold text-slate-500 uppercase flex items-center">
          Bác Sĩ
        </div>
        {dates.map((col, idx) => (
          <div key={idx} className={clsx("p-4 text-center border-l border-slate-100", col.isToday && "bg-sky-50/50")}>
            <div className={clsx("text-sm font-bold mb-1", col.isToday ? "text-sky-700" : "text-slate-800")}>{col.day}</div>
            <div className={clsx("text-xs font-medium", col.isToday ? "text-sky-600" : "text-slate-500")}>{col.date}</div>
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {!doctor ? (
          <div className="p-8 text-center text-slate-500">Vui lòng chọn bác sĩ để xem lịch làm việc.</div>
        ) : (
          <div className="grid grid-cols-[1.5fr_repeat(7,1fr)] border-b border-slate-100 hover:bg-slate-50/50 transition-colors h-full">
            <div className="p-4 flex flex-col pt-8">
              <h4 className="font-bold text-slate-900 text-sm">{doctor.title ? \\ \ : ''}{doctor.full_name}</h4>
              <p className="text-[11px] font-semibold text-sky-600 mt-0.5">Mã: {doctor.code}</p>
            </div>
            
            {dates.map((d, i) => {
              // Find schedules for this day
              const daySchedules = schedules.filter(s => s.starts_at.startsWith(d.iso));
              return (
                <div key={i} className={clsx("p-3 border-l", d.isToday ? "border-sky-100 bg-sky-50/20" : "border-slate-100")}>
                  {daySchedules.length > 0 ? (
                    <div className="flex flex-col gap-2">
                      {daySchedules.map(sch => (
                        <div key={sch.id} className="bg-slate-50 rounded-xl p-3 border border-slate-200 flex flex-col justify-between">
                          <div className="text-xs font-semibold text-slate-700 mb-1">
                            {new Date(sch.starts_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})} - {new Date(sch.ends_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})}
                          </div>
                          <div className={clsx("text-[10px] font-bold", sch.capacity > 0 ? "text-teal-600" : "text-rose-600")}>
                            {sch.capacity > 0 ? \Còn \ slot\ : 'Đã kín'}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <button className="w-full h-32 border-2 border-dashed border-slate-200 hover:border-sky-400 hover:bg-sky-50 rounded-xl flex flex-col items-center justify-center gap-1 text-slate-400 hover:text-sky-600 transition-colors">
                      <Plus size={20} />
                      <span className="text-xs font-semibold">Thêm ca</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between mt-auto">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center">
            <ShieldAlert size={20} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-800">Chế độ phân bổ thông minh HITL</h4>
            <p className="text-xs text-slate-500">Lịch ca trực luôn tuân thủ quy chế 48 giờ nghỉ liên tục của Bộ Y Tế.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
;

fs.writeFileSync(indexFile, indexCode, 'utf8');
fs.writeFileSync(sidebarFile, sidebarCode, 'utf8');
fs.writeFileSync(matrixFile, matrixCode, 'utf8');

console.log("Updated DoctorSchedule files");
