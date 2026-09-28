import React from 'react';
import { Eye, Calendar, Edit2, MoreVertical, Star, MapPin } from 'lucide-react';
import { Doctor } from './types';

interface DoctorTableProps {
  doctors: Doctor[];
}

export function DoctorTable({ doctors }: DoctorTableProps) {
  const getStatusBadge = (status: Doctor['status']) => {
    switch (status) {
      case 'ready':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-teal-50 border border-teal-100 text-teal-700 text-xs font-medium rounded-full"><span className="w-1.5 h-1.5 bg-teal-500 rounded-full"></span>Sẵn sàng tiếp nhận</span>;
      case 'examining':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-sky-50 border border-sky-100 text-sky-700 text-xs font-medium rounded-full"><span className="w-1.5 h-1.5 bg-sky-500 rounded-full"></span>Đang khám lâm sàng</span>;
      case 'emergency':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-50 border border-rose-100 text-rose-700 text-xs font-medium rounded-full"><span className="w-1.5 h-1.5 bg-rose-500 rounded-full"></span>Đang trực cấp cứu</span>;
      case 'full':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium rounded-full"><span className="w-1.5 h-1.5 bg-slate-400 rounded-full"></span>Lịch kín tuần</span>;
      case 'leave':
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-200 text-slate-500 text-xs font-medium rounded-full"><span className="w-1.5 h-1.5 bg-slate-300 rounded-full"></span>Nghỉ phép thường niên</span>;
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider w-[35%]">Bác sĩ & Học vị</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider">Mã CCHN & Hồ sơ</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider">Chuyên khoa & Trực thuộc</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider">Lâm sàng tháng</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider">Đánh giá</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider">Trạng thái ca</th>
            <th className="py-4 px-6 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {doctors.map(doc => (
            <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors group">
              <td className="py-4 px-6">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <img src={doc.avatarUrl} alt={doc.name} className="w-12 h-12 rounded-full object-cover border border-slate-200" />
                    {doc.status === 'ready' && <div className="absolute bottom-0 right-0 w-3 h-3 bg-teal-500 border-2 border-white rounded-full"></div>}
                    {doc.status === 'examining' && <div className="absolute bottom-0 right-0 w-3 h-3 bg-sky-500 border-2 border-white rounded-full"></div>}
                    {doc.status === 'emergency' && <div className="absolute bottom-0 right-0 w-3 h-3 bg-rose-500 border-2 border-white rounded-full"></div>}
                    {doc.status === 'full' && <div className="absolute bottom-0 right-0 w-3 h-3 bg-slate-400 border-2 border-white rounded-full"></div>}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-slate-900">{doc.name}</p>
                      {doc.isHitlLead && (
                        <span className="px-1.5 py-0.5 bg-indigo-50 border border-indigo-100 text-indigo-700 text-[10px] font-bold rounded">HITL Lead</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{doc.title} • {doc.experienceYears} năm KN</p>
                  </div>
                </div>
              </td>
              <td className="py-4 px-6">
                <p className="text-sm font-semibold text-slate-900">{doc.id}</p>
                <p className="text-xs text-slate-500 mt-1">CCHN:<br/>{doc.licenseNumber}</p>
              </td>
              <td className="py-4 px-6">
                <p className="text-sm font-semibold text-sky-700">{doc.specialty}</p>
                <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                  <MapPin size={12} /> {doc.facility}
                </p>
              </td>
              <td className="py-4 px-6">
                <p className="text-sm font-semibold text-slate-900">{doc.casesMonth} ca</p>
                <p className={`text-xs mt-1 font-medium ${doc.status === 'emergency' ? 'text-slate-600' : 'text-teal-600'}`}>
                  {doc.clinicalMetric}
                </p>
              </td>
              <td className="py-4 px-6">
                <div className="flex items-center gap-1.5">
                  <Star size={16} className="text-amber-400 fill-amber-400" />
                  <span className="text-sm font-bold text-slate-900">{doc.rating}</span>
                  <span className="text-xs text-slate-400">({doc.reviewCount})</span>
                </div>
              </td>
              <td className="py-4 px-6">
                {getStatusBadge(doc.status)}
              </td>
              <td className="py-4 px-6 text-right">
                <div className="flex items-center justify-end gap-2 text-slate-400">
                  <button className="p-1.5 hover:bg-slate-100 hover:text-sky-600 rounded-md transition-colors"><Eye size={18} /></button>
                  <button className="p-1.5 hover:bg-slate-100 hover:text-sky-600 rounded-md transition-colors"><Calendar size={18} /></button>
                  <button className="p-1.5 hover:bg-slate-100 hover:text-sky-600 rounded-md transition-colors"><Edit2 size={18} /></button>
                  <button className="p-1.5 hover:bg-slate-100 hover:text-slate-700 rounded-md transition-colors"><MoreVertical size={18} /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">Hiển thị</span>
          <select className="border border-slate-200 rounded-md text-sm py-1 px-2 bg-slate-50 focus:outline-none focus:border-sky-500">
            <option>10 bác sĩ / trang</option>
          </select>
          <span className="text-sm text-slate-500">bản ghi trên tổng số 148 bác sĩ</span>
        </div>
        
        <div className="flex items-center gap-1">
          <button className="p-1 text-slate-400 hover:text-slate-700">«</button>
          <button className="w-8 h-8 rounded-lg bg-teal-700 text-white font-medium text-sm flex items-center justify-center">1</button>
          <button className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-700 font-medium text-sm flex items-center justify-center transition-colors">2</button>
          <button className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-700 font-medium text-sm flex items-center justify-center transition-colors">3</button>
          <span className="px-2 text-slate-400">...</span>
          <button className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-700 font-medium text-sm flex items-center justify-center transition-colors">15</button>
          <button className="p-1 text-slate-400 hover:text-slate-700">»</button>
        </div>
      </div>
    </div>
  );
}
