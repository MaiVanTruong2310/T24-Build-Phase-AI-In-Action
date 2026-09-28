import React from 'react';
import { Lock, FileSignature, BookOpen, Clock, Activity, Check } from 'lucide-react';
import { DoctorForm, FieldErrors } from './FormTypes';

interface Props {
  form: DoctorForm;
  errors: FieldErrors;
  onChange: (field: keyof DoctorForm, value: string | boolean) => void;
}

export function PermissionsSection({ form, onChange }: Props) {
  const isLevel1 = form.permissionLevel === 'level1';
  const isLevel2 = form.permissionLevel === 'level2';
  const isLevel3 = form.permissionLevel === 'level3';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-700 text-white rounded-lg">
            <Lock size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">4. Phân quyền Hệ thống & Duyệt Y lệnh AI (HITL Protocol)</h2>
            <p className="text-xs text-slate-500">Quy định thẩm quyền pháp lý đối với các gợi ý phác đồ từ trợ lý AI MediCare</p>
          </div>
        </div>
        <span className="px-2 py-1 bg-teal-100 text-teal-700 text-xs font-bold rounded">Bảo mật cấp 4</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Cấp 1 */}
        <div 
          onClick={() => onChange('permissionLevel', 'level1')}
          className={`cursor-pointer rounded-xl border-2 p-4 transition-all relative ${isLevel1 ? 'border-sky-500 bg-sky-50/30 shadow-md' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}
        >
          {isLevel1 && <div className="absolute top-3 right-3 text-sky-500"><Check size={20} /></div>}
          <span className="text-xs font-bold text-sky-600 mb-1 block">CẤP 1</span>
          <h3 className="text-base font-bold text-slate-900 mb-2">Lead Clinician</h3>
          <p className="text-xs text-slate-600 mb-4 h-16">Toàn quyền ký duyệt độc lập phác đồ điều trị nguy kịch, kê toa nhóm thuốc đặc trị kiểm soát đặc biệt và ký y lệnh phẫu thuật.</p>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-700">
            <FileSignature size={14} />
            Ký số PKI Cloud
          </div>
        </div>

        {/* Cấp 2 */}
        <div 
          onClick={() => onChange('permissionLevel', 'level2')}
          className={`cursor-pointer rounded-xl border-2 p-4 transition-all relative ${isLevel2 ? 'border-sky-500 bg-sky-50/30 shadow-md' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}
        >
          {isLevel2 && <div className="absolute top-3 right-3 text-sky-500"><Check size={20} /></div>}
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-slate-500">CẤP 2</span>
            <BookOpen size={16} className="text-slate-400" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mb-2">Bác sĩ Chuyên khoa</h3>
          <p className="text-xs text-slate-600 mb-4 h-16">Duyệt phác đồ khám ngoại trú trong phạm vi chuyên khoa được giao. Đơn thuốc đặc trị cần đồng thuận từ Bác sĩ Cấp 1.</p>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-700">
            <Check size={14} />
            Phạm vi khoa
          </div>
        </div>

        {/* Cấp 3 */}
        <div 
          onClick={() => onChange('permissionLevel', 'level3')}
          className={`cursor-pointer rounded-xl border-2 p-4 transition-all relative ${isLevel3 ? 'border-sky-500 bg-sky-50/30 shadow-md' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}
        >
          {isLevel3 && <div className="absolute top-3 right-3 text-sky-500"><Check size={20} /></div>}
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-slate-500">CẤP 3</span>
            <Clock size={16} className="text-slate-400" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mb-2">Tư vấn Lâm sàng</h3>
          <p className="text-xs text-slate-600 mb-4 h-16">Tiếp nhận phân luồng triage ban đầu, tư vấn khám từ xa, không có quyền chốt toa thuốc can thiệp chuyên sâu độc lập.</p>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-700">
            <Activity size={14} />
            Chỉ đọc & sơ khám
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Đơn giá khám tiêu chuẩn (BHYT / Khám công)</label>
          <div className="relative">
            <input 
              type="text" 
              value={form.standardPrice}
              onChange={(e) => onChange('standardPrice', e.target.value)}
              placeholder="150.000"
              className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold text-slate-900 focus:outline-none focus:border-sky-500"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-slate-500">VNĐ / Lượt</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1.5">Đơn giá khám chuyên gia VIP / Yêu cầu cao</label>
          <div className="relative">
            <input 
              type="text" 
              value={form.vipPrice}
              onChange={(e) => onChange('vipPrice', e.target.value)}
              placeholder="450.000"
              className="w-full px-4 py-2 bg-sky-50 border border-sky-100 rounded-lg text-sm font-semibold text-sky-800 focus:outline-none focus:border-sky-500"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-slate-500">VNĐ / Lượt</span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <label className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
          <input 
            type="checkbox" 
            checked={form.allowOnlineBooking}
            onChange={(e) => onChange('allowOnlineBooking', e.target.checked)}
            className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500"
          />
          <div>
            <p className="text-sm font-bold text-slate-900">Cho phép người bệnh chủ động đặt lịch khám trực tuyến qua Ứng dụng Bệnh Nhân</p>
            <p className="text-xs text-slate-500 mt-0.5">Lịch hẹn tự động đồng bộ theo khung giờ rảnh và quy tắc dãn cách chống quá tải</p>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
          <input 
            type="checkbox" 
            checked={form.enableEmergencyCode}
            onChange={(e) => onChange('enableEmergencyCode', e.target.checked)}
            className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500"
          />
          <div>
            <p className="text-sm font-bold text-slate-900">Kích hoạt chế độ sẵn sàng tham gia kíp can thiệp cấp cứu khẩn cấp (Emergency Code Red)</p>
            <p className="text-xs text-slate-500 mt-0.5">Nhận cuộc gọi khẩn và báo động y khoa ưu tiên qua vòng đeo tay y tế MediCare IoT</p>
          </div>
        </label>
      </div>
    </div>
  );
}
