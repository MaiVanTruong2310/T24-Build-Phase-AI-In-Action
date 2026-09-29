import React from 'react';
import { Download, Calendar, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Header() {
  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
          <span className="text-sky-600 font-medium bg-sky-50 px-2 py-0.5 rounded-full flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-600"></span>
            Cơ sở Dữ liệu Lâm sàng Quốc gia
          </span>
          <span className="text-slate-400">•</span>
          <span>Đồng bộ thời gian thực (HITL Verified)</span>
        </div>
        <h1 className="text-3xl font-bold text-slate-900">Hồ Sơ & Điều Phối Bác Sĩ</h1>
        <p className="text-slate-500 mt-1 max-w-2xl text-sm">
          Quản lý danh bộ 148 chuyên gia y tế, điều phối ca lâm sàng tự động bằng thuật toán MediCare AI và giám sát chỉ số an toàn khám chữa bệnh.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium text-sm transition-colors">
          <Download size={16} /> Xuất Báo Cáo KPI
        </button>
        <button className="flex items-center gap-2 px-4 py-2 bg-teal-700 text-white rounded-lg hover:bg-teal-800 font-medium text-sm transition-colors">
          <Calendar size={16} /> Phân Bổ Lịch Trực AI
        </button>
        <Link to="/staff/doctors/create" className="flex items-center gap-2 px-4 py-2 bg-sky-700 text-white rounded-lg hover:bg-sky-800 font-medium text-sm transition-colors">
          <Plus size={16} /> Thêm Bác Sĩ Mới
        </Link>
      </div>
    </div>
  );
}
