import React from 'react';
import { Share2 } from 'lucide-react';
import { DoctorForm } from './FormTypes';
import { Specialty } from '../api';

interface Props {
  form: DoctorForm;
  specialties: Specialty[];
}

export function PreviewSidebar({ form, specialties }: Props) {
  const selectedSpecialty = specialties.find(s => s.id === form.specialty)?.name;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6">
      <div className="bg-sky-700 p-3 flex items-center justify-between">
        <span className="text-xs font-semibold text-white flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
          Xem trước thời gian thực
        </span>
        <button className="text-white/80 hover:text-white"><Share2 size={16} /></button>
      </div>

      <div className="p-6 text-center border-b border-slate-100 relative">
        <img src="https://i.pravatar.cc/150?u=bs1082" alt="Doctor" className="w-20 h-20 rounded-full mx-auto border-2 border-white shadow-md object-cover mb-3" />
        <p className="text-xs font-bold text-sky-600 uppercase mb-1">{form.academicTitle || 'BSCKII.'}</p>
        <h3 className="text-lg font-bold text-slate-900 mb-1">{form.fullName || 'Nguyễn Hoàng Nam'}</h3>
        <p className="text-sm text-slate-500 mb-3">{selectedSpecialty || 'Chưa chọn chuyên khoa'}</p>
        
        <div className="flex items-center justify-center gap-2">
          <span className="px-2 py-0.5 bg-teal-50 text-teal-700 rounded text-xs font-semibold flex items-center gap-1">
            Trưởng khoa
          </span>
          <span className="px-2 py-0.5 bg-sky-50 text-sky-700 rounded text-xs font-semibold flex items-center gap-1">
            {form.experienceYears || 16} năm KN
          </span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        <div className="flex justify-between items-center pb-3 border-b border-slate-100">
          <div>
            <p className="text-[10px] text-slate-500 uppercase font-semibold">Số hiệu CCHN</p>
            <p className="text-sm font-bold text-slate-900 mt-0.5">{form.licenseNumber || '004819/BYT-CCHN'}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-slate-500 uppercase font-semibold">Quyền duyệt AI</p>
            <p className="text-sm font-bold text-sky-700 mt-0.5">{form.permissionLevel === 'level1' ? 'Cấp 1 - Lead' : form.permissionLevel === 'level2' ? 'Cấp 2' : 'Cấp 3'}</p>
          </div>
        </div>

        <div>
          <p className="text-[10px] text-slate-500 uppercase font-semibold">Phòng khám điều phối</p>
          <p className="text-sm font-medium text-slate-800 mt-0.5">{form.defaultRoom || 'Phòng 304 - Khu Can thiệp mạch Tim'}</p>
        </div>

        <div>
          <p className="text-[10px] text-slate-500 uppercase font-semibold">Cơ sở phục vụ</p>
          <p className="text-sm font-medium text-slate-800 mt-0.5">{form.facility || 'Cơ sở 1 - Q.10'}</p>
        </div>

        <div className="pt-2">
          <div className="flex justify-between items-center mb-1">
            <p className="text-xs font-semibold text-slate-700">Hạn mức chỉ định cận lâm sàng AI</p>
            <p className="text-xs font-bold text-sky-600">100% (Không giới hạn)</p>
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-sky-400 to-sky-600 w-full rounded-full"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
