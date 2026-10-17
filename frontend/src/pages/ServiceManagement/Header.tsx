import React from 'react';
import { Link } from 'react-router-dom';
import { Download, Plus, FileText, CheckCircle2 } from 'lucide-react';

export function Header({ onExport }: { onExport: () => void }) {
  return (
    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Quản Lý Gói Dịch Vụ Khám Y Tế</h1>
        <p className="text-sm text-slate-500">Quản lý bảng giá, danh mục kỹ thuật xét nghiệm/thăm dò chức năng và điều phối thuật toán AI phân loại bệnh nhân theo gói khám chuyên khoa.</p>
        <div className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 bg-teal-100 text-teal-700 rounded-full text-xs font-medium">
          <CheckCircle2 size={14} />
          Đồng bộ EHR & Portal
        </div>
      </div>
      
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" disabled title="Chức năng khuyến mãi chưa được hỗ trợ" aria-label="Khuyến mãi chưa được hỗ trợ" className="flex items-center gap-2 px-4 py-2 bg-rose-50 text-rose-600 rounded-lg text-sm font-semibold hover:bg-rose-100 transition-colors">
          <FileText size={18} />
          Khuyến mãi & Mã ưu đãi <span className="bg-rose-500 text-white text-[10px] px-1.5 py-0.5 rounded ml-1">3 Đang chạy</span>
        </button>
        <button type="button" onClick={onExport} className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
          <Download size={18} />
          Xuất Excel Biểu Phí
        </button>
        <Link 
          to="/staff/services/create"
          className="flex items-center gap-2 px-4 py-2 bg-sky-700 text-white rounded-lg text-sm font-semibold hover:bg-sky-800 transition-colors shadow-sm"
        >
          <Plus size={18} />
          + Tạo Gói Dịch Vụ Mới
        </Link>
      </div>
    </div>
  );
}
