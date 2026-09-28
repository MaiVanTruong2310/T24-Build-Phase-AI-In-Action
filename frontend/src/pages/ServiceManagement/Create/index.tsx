import React, { useState } from 'react';
import { ShieldCheck, Save } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { ServiceFormSection } from './ServiceFormSection';
import { PreviewSidebar } from './PreviewSidebar';
import { createService } from '../api';

export interface ServiceForm {
  code: string;
  name: string;
  description: string;
  duration_minutes: number;
}

export default function CreateService() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<ServiceForm>({
    code: '',
    name: '',
    description: '',
    duration_minutes: 30
  });

  const [errors, setErrors] = useState<Partial<Record<keyof ServiceForm, string>>>({});

  const handleFieldChange = (field: keyof ServiceForm, value: string | number) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = () => {
    const newErrors: Partial<Record<keyof ServiceForm, string>> = {};
    if (!form.code) newErrors.code = 'Mã dịch vụ là bắt buộc';
    if (!form.name) newErrors.name = 'Tên dịch vụ là bắt buộc';
    if (!form.duration_minutes || form.duration_minutes <= 0) newErrors.duration_minutes = 'Thời gian dự kiến không hợp lệ';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    
    const result = await createService({
      code: form.code,
      name: form.name,
      description: form.description,
      duration_minutes: Number(form.duration_minutes)
    })();

    setIsSubmitting(false);

    if (result._tag === 'Right') {
      alert('Tạo dịch vụ thành công!');
      navigate('/staff/services');
    } else {
      alert('Lỗi tạo dịch vụ: ' + result.left.message);
    }
  };

  return (
    <div className="flex-1 bg-slate-50 min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            <span>Quản trị hệ thống</span>
            <span>/</span>
            <Link to="/staff/services" className="hover:text-sky-600 transition-colors">Quản Lý Gói Dịch Vụ Y Tế</Link>
            <span>/</span>
            <span className="text-sky-700">Thêm mới dịch vụ</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Thêm Mới Dịch Vụ Khám</h1>
          <p className="text-sm text-slate-500">Khai báo thông tin gói khám, thời gian thực hiện và mô tả chuyên môn.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-sky-50 text-sky-700 rounded-lg text-xs font-bold border border-sky-100">
            <ShieldCheck size={16} /> HITL Enabled
          </div>
          <button 
            type="button"
            className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors"
          >
            Lưu nháp
          </button>
          <Link
            to="/staff/services"
            className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors"
          >
            Hủy bỏ
          </Link>
          <button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2 bg-sky-700 text-white rounded-lg text-sm font-semibold hover:bg-sky-800 transition-colors shadow-sm disabled:opacity-70"
          >
            <Save size={18} />
            {isSubmitting ? 'Đang lưu...' : 'Kích hoạt & Lưu hồ sơ'}
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Form Container */}
        <div className="flex-1">
          <form onSubmit={handleSubmit} className="space-y-6">
            <ServiceFormSection form={form} errors={errors} onChange={handleFieldChange} />
          </form>
        </div>
        
        {/* Sidebar */}
        <div className="w-full lg:w-[320px] flex-shrink-0">
          <div className="sticky top-6">
            <PreviewSidebar form={form} />
          </div>
        </div>
      </div>
    </div>
  );
}
