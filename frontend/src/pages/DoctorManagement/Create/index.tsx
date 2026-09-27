import React, { useState, useEffect } from 'react';
import { ShieldCheck, Save } from 'lucide-react';
import * as E from 'fp-ts/Either';
import { DoctorForm, FieldErrors } from './FormTypes';
import { validateDoctorForm } from './FormValidation';
import { PersonalInfoSection } from './PersonalInfoSection';
import { LegalProfileSection } from './LegalProfileSection';
import { OrganizationSection } from './OrganizationSection';
import { PermissionsSection } from './PermissionsSection';
import { PreviewSidebar } from './PreviewSidebar';
import { ValidationSidebar } from './ValidationSidebar';
import { createDoctor, fetchSpecialties, Specialty } from '../api';

export default function CreateDoctor() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [form, setForm] = useState<DoctorForm>({
    fullName: '',
    academicTitle: 'BSCKII',
    gender: 'Nam',
    dateOfBirth: '',
    idNumber: '',
    phone: '',
    email: '',
    licenseNumber: '',
    licenseIssueDate: '',
    licenseIssuer: 'Bộ Y Tế Việt Nam',
    practiceScope: '',
    experienceYears: '',
    facility: 'Cơ sở 1 - Trung tâm Đa khoa Q.10 (312 Nguyễn Tri Phương)',
    specialty: '',
    position: '',
    defaultRoom: '',
    permissionLevel: 'level1',
    standardPrice: '150.000',
    vipPrice: '450.000',
    allowOnlineBooking: true,
    enableEmergencyCode: true,
  });

  const [errors, setErrors] = useState<FieldErrors>({});
  const [specialties, setSpecialties] = useState<Specialty[]>([]);

  useEffect(() => {
    const loadSpecialties = async () => {
      const result = await fetchSpecialties()();
      if (result._tag === 'Right') {
        setSpecialties(result.right);
      }
    };
    loadSpecialties();
  }, []);

  const handleFieldChange = (field: keyof DoctorForm, value: string | boolean) => {
    setForm(prev => ({ ...prev, [field]: value }));
    // Clear error when user types
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationResult = validateDoctorForm(form);
    
    if (E.isLeft(validationResult)) {
      setErrors(validationResult.left);
      // Optional: scroll to first error
    } else {
      setSubmitError(null);
      setIsSubmitting(true);
      
      const payload = {
        full_name: form.fullName,
        code: `DOC-${Date.now().toString().slice(-6)}`,
        license_number: form.licenseNumber || null,
        email: form.email || null,
        phone: form.phone || null,
        bio: form.practiceScope || null,
        status: 'active',
        review_status: 'approved',
        booking_enabled: form.allowOnlineBooking,
        avatar_url: null,
        gender: form.gender,
        title: form.academicTitle,
        date_of_birth: form.dateOfBirth || null,
        specialty_ids: form.specialty ? [form.specialty] : [],
        facilities: [],
        service_ids: []
      };

      const task = createDoctor(payload);
      const result = await task();

      setIsSubmitting(false);

      if (result._tag === 'Right') {
        alert('Đã lưu hồ sơ thành công!');
        // Could redirect to list here
      } else {
        setSubmitError(result.left.message);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 p-6">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center text-xs text-slate-500 mb-2">
            <span>Quản trị hệ thống</span>
            <span className="mx-2">/</span>
            <span>Quản Lý Bác Sĩ</span>
            <span className="mx-2">/</span>
            <span className="text-sky-600 font-semibold">Thêm mới bác sĩ</span>
          </div>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">Thêm Mới Hồ Sơ Bác Sĩ & Cấp Quyền Lâm Sàng</h1>
                <span className="px-2 py-1 bg-sky-100 text-sky-700 text-xs font-bold rounded-lg flex items-center gap-1">
                  <ShieldCheck size={14} /> HITL Enabled
                </span>
              </div>
              <p className="text-sm text-slate-600 mt-1">Khai báo thông tin định danh y tế, chứng chỉ hành nghề (CCHN), phân bổ chuyên khoa và cấp quyền duyệt y lệnh AI độc lập trong phân hệ khám bệnh.</p>
            </div>
            
            <div className="flex items-center gap-3">
              {submitError && <span className="text-sm text-rose-600">{submitError}</span>}
              <button className="px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition-colors">
                Lưu nháp
              </button>
              <button className="px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition-colors">
                Hủy bỏ
              </button>
              <button 
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-4 py-2 bg-sky-700 text-white text-sm font-semibold rounded-lg hover:bg-sky-800 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Save size={16} />
                {isSubmitting ? 'Đang lưu...' : 'Kích hoạt & Lưu hồ sơ bác sĩ'}
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main Form */}
          <div className="flex-1">
            <form onSubmit={handleSubmit}>
              <PersonalInfoSection form={form} errors={errors} onChange={handleFieldChange} />
              <LegalProfileSection form={form} errors={errors} onChange={handleFieldChange} />
              <OrganizationSection form={form} errors={errors} onChange={handleFieldChange} specialties={specialties} />
              <PermissionsSection form={form} errors={errors} onChange={handleFieldChange} />
            </form>
          </div>

          {/* Sidebar */}
          <div className="w-full lg:w-[320px] flex-shrink-0">
            <div className="sticky top-6">
              <PreviewSidebar form={form} specialties={specialties} />
              <ValidationSidebar />
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
