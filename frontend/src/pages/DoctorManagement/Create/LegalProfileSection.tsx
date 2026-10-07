import React from 'react';
import { ShieldCheck, CloudUpload, FileText, CheckCircle2 } from 'lucide-react';
import { DoctorForm, FieldErrors } from './FormTypes';
import { formatDateVN } from '../../../features/appointment-booking/dateValidation';
import { DateInputVN } from '../../../components/DateInputVN';

interface Props {
  form: DoctorForm;
  errors: FieldErrors;
  onChange: (field: keyof DoctorForm, value: string) => void;
}

export function LegalProfileSection({ form, errors, onChange }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
          <ShieldCheck size={20} />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">2. Hồ sơ Pháp lý Y tế & Chứng chỉ hành nghề (CCHN)</h2>
          <p className="text-xs text-slate-500">Thông tin xác minh tự động với CSDL Y bạ điện tử Quốc gia</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-4 mb-6">
        {/* Số CCHN */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Số CCHN Quốc Gia <span className="text-rose-500">*</span></label>
          <input 
            type="text" 
            value={form.licenseNumber}
            onChange={(e) => onChange('licenseNumber', e.target.value)}
            placeholder="004819/BYT-CCHN"
            className={`w-full px-4 py-2 text-sky-700 font-semibold bg-sky-50/50 border ${errors.licenseNumber ? 'border-rose-500 ring-1 ring-rose-500' : 'border-sky-100'} rounded-lg text-sm focus:outline-none focus:border-sky-500`}
          />
          {errors.licenseNumber && <p className="mt-1 text-xs text-rose-500">{errors.licenseNumber}</p>}
        </div>

        {/* Ngày cấp */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm font-semibold text-slate-900">
              Ngày cấp CCHN <span className="text-rose-500">*</span> <span className="text-xs font-normal text-slate-500">(dd/mm/yyyy)</span>
            </label>
            {form.licenseIssueDate && (
              <span className="text-xs text-teal-600 font-medium">
                {formatDateVN(form.licenseIssueDate)}
              </span>
            )}
          </div>
          <DateInputVN 
            max={new Date().toISOString().split('T')[0]}
            value={form.licenseIssueDate}
            onChange={(e) => onChange('licenseIssueDate', e.target.value)}
            hasError={Boolean(errors.licenseIssueDate)}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Cơ quan cấp */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Cơ quan cấp CCHN <span className="text-rose-500">*</span></label>
          <input 
            type="text" 
            value={form.licenseIssuer}
            onChange={(e) => onChange('licenseIssuer', e.target.value)}
            placeholder="Bộ Y Tế Việt Nam"
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Phạm vi hoạt động */}
        <div className="md:col-span-2">
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Phạm vi hoạt động chuyên môn y tế được cấp phép <span className="text-rose-500">*</span></label>
          <input 
            type="text" 
            value={form.practiceScope}
            onChange={(e) => onChange('practiceScope', e.target.value)}
            placeholder="Khám chữa bệnh chuyên khoa Tim mạch và Can thiệp Tim mạch nội khoa"
            className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Số năm KN */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Số năm kinh nghiệm <span className="text-rose-500">*</span></label>
          <div className="relative">
            <input 
              type="text" 
              value={form.experienceYears}
              onChange={(e) => onChange('experienceYears', e.target.value)}
              placeholder="16"
              className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500 text-right pr-12"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-slate-400">Năm</span>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-900 mb-3">Văn bằng, Bằng cấp chuyên khoa & Bản quét CCHN công chứng</label>
        <div className="border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:bg-slate-100 transition-colors cursor-pointer mb-4">
          <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center text-sky-600 mb-3">
            <CloudUpload size={24} />
          </div>
          <p className="text-sm font-bold text-slate-900">Kéo và thả tệp PDF, scan CCHN hoặc click để chọn tệp</p>
          <p className="text-xs text-slate-500 mt-1">Hỗ trợ PDF, PNG, JPG (Dung lượng mỗi file tối đa 15MB)</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Mock uploaded files */}
          <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg flex items-center justify-between group">
            <div className="flex items-center gap-3">
              <FileText className="text-rose-500" size={24} />
              <div>
                <p className="text-sm font-semibold text-slate-700 group-hover:text-sky-600 transition-colors cursor-pointer">CCHN_NguyenHoangNam_2024.pdf</p>
                <p className="text-xs text-slate-500">3.4 MB • Đã xác thực OCR</p>
              </div>
            </div>
            <CheckCircle2 size={16} className="text-teal-500" />
          </div>

          <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg flex items-center justify-between group">
            <div className="flex items-center gap-3">
              <FileText className="text-sky-500" size={24} />
              <div>
                <p className="text-sm font-semibold text-slate-700 group-hover:text-sky-600 transition-colors cursor-pointer">Bang_BSCKII_TimMach_YDuoc.pdf</p>
                <p className="text-xs text-slate-500">5.1 MB • Bản ký số gốc</p>
              </div>
            </div>
            <CheckCircle2 size={16} className="text-teal-500" />
          </div>
        </div>
      </div>
    </div>
  );
}
