import React from 'react';
import { Building, Briefcase } from 'lucide-react';
import { DoctorForm, FieldErrors } from './FormTypes';
import { Specialty } from '../api';

interface Props {
  form: DoctorForm;
  errors: FieldErrors;
  onChange: (field: keyof DoctorForm, value: string) => void;
  specialties: Specialty[];
}

export function OrganizationSection({ form, onChange, specialties }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
            <Building size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">3. Phân bổ Tổ chức & Địa bàn công tác</h2>
            <p className="text-xs text-slate-500">Cấu hình chi nhánh bệnh viện, khoa phòng phụ trách và bàn khám đón tiếp</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
        {/* Cơ sở */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Cơ sở bệnh viện trực thuộc <span className="text-rose-500">*</span></label>
          <div className="relative">
            <select 
              value={form.facility}
              onChange={(e) => onChange('facility', e.target.value)}
              className="w-full appearance-none pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
            >
              <option value="Cơ sở 1 - Trung tâm Đa khoa Q.10 (312 Nguyễn Tri Phương)">Cơ sở 1 - Trung tâm Đa khoa Q.10 (312 Nguyễn Tri Phương)</option>
              <option value="Cơ sở 2">Cơ sở 2</option>
            </select>
            <Building size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          </div>
        </div>

        {/* Chuyên khoa */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Chuyên khoa công tác chính <span className="text-rose-500">*</span></label>
          <div className="relative">
            <select 
              value={form.specialty}
              onChange={(e) => onChange('specialty', e.target.value)}
              className="w-full appearance-none pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
            >
              <option value="" disabled>-- Chọn chuyên khoa --</option>
              {specialties.map(spec => (
                <option key={spec.id} value={spec.id}>{spec.name}</option>
              ))}
            </select>
            <Briefcase size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          </div>
        </div>

        {/* Chức vụ */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Chức vụ đảm nhiệm tại khoa <span className="text-rose-500">*</span></label>
          <input 
            type="text" 
            value={form.position}
            onChange={(e) => onChange('position', e.target.value)}
            placeholder="Trưởng khoa Lâm sàng"
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Phòng khám */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Phòng khám mặc định điều phối <span className="text-rose-500">*</span></label>
          <input 
            type="text" 
            value={form.defaultRoom}
            onChange={(e) => onChange('defaultRoom', e.target.value)}
            placeholder="Phòng 304 - Khu Can thiệp mạch Tim"
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>
    </div>
  );
}
