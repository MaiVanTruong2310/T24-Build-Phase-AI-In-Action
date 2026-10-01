import React from 'react';
import { Camera, User, FileBadge2, CreditCard, Phone, Mail } from 'lucide-react';
import { DoctorForm, FieldErrors } from './FormTypes';

interface Props {
  form: DoctorForm;
  errors: FieldErrors;
  onChange: (field: keyof DoctorForm, value: string) => void;
}

export function PersonalInfoSection({ form, errors, onChange }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <User size={20} />
          </div>
          <h2 className="text-lg font-bold text-slate-900">1. Thông tin nhân sự & Định danh cá nhân</h2>
        </div>
        <span className="text-sm font-medium text-rose-600">* (*) Bắt buộc</span>
      </div>

      <div className="flex items-start gap-6 mb-8">
        <div className="relative">
          <img src="https://i.pravatar.cc/150?u=bs1082" alt="Avatar" className="w-24 h-24 rounded-full object-cover border-4 border-slate-50" />
          <button className="absolute bottom-0 right-0 p-1.5 bg-sky-700 text-white rounded-full border-2 border-white hover:bg-sky-800">
            <Camera size={14} />
          </button>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-slate-900">Ảnh chân dung bác sĩ (Blouse trắng chuẩn y khoa)</h3>
          <p className="text-xs text-slate-500 mt-1">Định dạng JPG, PNG dung lượng không quá 5MB. Khuyên nghị chụp trên phông nền trắng hoặc xanh y tế nhất để hiển thị tối ưu trên App bệnh nhân.</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">Tỷ lệ: 1:1</span>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">Độ phân giải: 600x600px+</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
        {/* Họ và tên */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Họ và tên bác sĩ <span className="text-rose-500">*</span></label>
          <div className="relative">
            <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              value={form.fullName}
              onChange={(e) => onChange('fullName', e.target.value)}
              placeholder="Nguyễn Hoàng Nam"
              className={`w-full pl-10 pr-4 py-2 bg-slate-50 border ${errors.fullName ? 'border-rose-500 ring-1 ring-rose-500' : 'border-slate-200'} rounded-lg text-sm focus:outline-none focus:border-sky-500 focus:bg-white transition-colors`}
            />
          </div>
          {errors.fullName && <p className="mt-1 text-xs text-rose-500">{errors.fullName}</p>}
        </div>

        {/* Học hàm */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Học hàm / Học vị y khoa <span className="text-rose-500">*</span></label>
          <div className="relative">
            <FileBadge2 size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select 
              value={form.academicTitle}
              onChange={(e) => onChange('academicTitle', e.target.value)}
              className={`w-full appearance-none pl-10 pr-4 py-2 bg-slate-50 border ${errors.academicTitle ? 'border-rose-500 ring-1 ring-rose-500' : 'border-slate-200'} rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500 focus:bg-white`}
            >
              <option value="BSCKII">Bác sĩ Chuyên khoa II (BSCKII)</option>
              <option value="PGS.TS">PGS. TS.</option>
              <option value="BSCKI">Bác sĩ Chuyên khoa I (BSCKI)</option>
            </select>
          </div>
          {errors.academicTitle && <p className="mt-1 text-xs text-rose-500">{errors.academicTitle}</p>}
        </div>

        {/* Giới tính */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Giới tính <span className="text-rose-500">*</span></label>
          <select 
            value={form.gender}
            onChange={(e) => onChange('gender', e.target.value)}
            className="w-full appearance-none px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500 focus:bg-white"
          >
            <option value="Nam">Nam</option>
            <option value="Nữ">Nữ</option>
          </select>
        </div>

        {/* Ngày sinh */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Ngày sinh <span className="text-rose-500">*</span></label>
          <input 
            type="date" 
            value={form.dateOfBirth}
            onChange={(e) => onChange('dateOfBirth', e.target.value)}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500 focus:bg-white"
          />
        </div>

        {/* Số CCCD */}
        <div className="md:col-span-2">
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Số CCCD / Mã định danh VNeID <span className="text-rose-500">*</span></label>
          <div className="relative">
            <CreditCard size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              value={form.idNumber}
              onChange={(e) => onChange('idNumber', e.target.value)}
              placeholder="079082001923"
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-sky-500 focus:bg-white"
            />
          </div>
        </div>

        {/* SĐT */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Số điện thoại liên lạc nội viện <span className="text-rose-500">*</span></label>
          <div className="relative">
            <Phone size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              value={form.phone}
              onChange={(e) => onChange('phone', e.target.value)}
              placeholder="0918 234 889"
              className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-sky-500 focus:bg-white"
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Email bệnh viện VCare+ <span className="text-rose-500">*</span></label>
          <div className="relative">
            <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="email" 
              value={form.email}
              onChange={(e) => onChange('email', e.target.value)}
              placeholder="nam.nguyenhoang@vcare.vn"
              className={`w-full pl-10 pr-4 py-2 bg-slate-50 border ${errors.email ? 'border-rose-500 ring-1 ring-rose-500' : 'border-slate-200'} rounded-lg text-sm focus:outline-none focus:border-sky-500 focus:bg-white`}
            />
          </div>
          {errors.email && <p className="mt-1 text-xs text-rose-500">{errors.email}</p>}
        </div>

      </div>
    </div>
  );
}
