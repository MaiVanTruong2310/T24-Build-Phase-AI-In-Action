import React from 'react';
import { Gavel, CheckCircle2, HelpCircle } from 'lucide-react';

export function ValidationSidebar() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
      <div className="flex justify-between items-center mb-5">
        <h3 className="font-bold text-slate-900 flex items-center gap-2">
          <Gavel size={18} className="text-teal-600" />
          Kiểm tra Pháp lý CCHN
        </h3>
        <span className="px-2 py-0.5 bg-teal-100 text-teal-800 text-[10px] font-bold rounded-full">Hoàn tất 3/3</span>
      </div>

      <div className="space-y-4">
        {/* Item 1 */}
        <div className="flex gap-3">
          <div className="mt-0.5">
            <div className="w-5 h-5 rounded-full bg-teal-500 text-white flex items-center justify-center">
              <CheckCircle2 size={12} />
            </div>
          </div>
          <div>
            <div className="flex justify-between items-start">
              <p className="text-sm font-bold text-slate-900">Tra cứu CSDL Bộ Y Tế</p>
              <span className="text-[10px] font-semibold text-teal-600">Hợp lệ</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Số CCHN đã đối soát trùng khớp họ tên và phạm vi hành nghề của Bộ Y tế công bố.</p>
          </div>
        </div>

        {/* Item 2 */}
        <div className="flex gap-3">
          <div className="mt-0.5">
            <div className="w-5 h-5 rounded-full bg-teal-500 text-white flex items-center justify-center">
              <CheckCircle2 size={12} />
            </div>
          </div>
          <div>
            <div className="flex justify-between items-start">
              <p className="text-sm font-bold text-slate-900">Kiểm tra trùng lịch kíp trực</p>
              <span className="text-[10px] font-semibold text-teal-600">Sẵn sàng</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Bác sĩ không vướng ca thường trực đồng thời tại các cơ sở bệnh viện trực thuộc khác.</p>
          </div>
        </div>

        {/* Item 3 */}
        <div className="flex gap-3">
          <div className="mt-0.5">
            <div className="w-5 h-5 rounded-full bg-teal-500 text-white flex items-center justify-center">
              <CheckCircle2 size={12} />
            </div>
          </div>
          <div>
            <div className="flex justify-between items-start">
              <p className="text-sm font-bold text-slate-900">Chứng thư Chữ ký số PKI</p>
              <span className="text-[10px] font-semibold text-teal-600">Khả dụng</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Chứng thư số HSM y tế được cấp phép bởi Ban Cơ yếu Chính phủ sẵn sàng kích hoạt.</p>
          </div>
        </div>
      </div>

      <div className="mt-5 p-3 bg-slate-50 rounded-lg flex items-start gap-2 border border-slate-100">
        <HelpCircle size={16} className="text-sky-600 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs font-bold text-slate-800">Cần giải đáp quy chế cấp quyền?</p>
          <p className="text-xs text-slate-500 mt-0.5">Liên hệ Hội đồng Y khoa theo số máy nhánh nội bộ <span className="font-semibold text-slate-700">#8088</span>.</p>
        </div>
      </div>
    </div>
  );
}
