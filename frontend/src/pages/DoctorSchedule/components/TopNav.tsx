import { Bell, Settings, Activity } from 'lucide-react';

export const TopNav = () => (
  <div className="bg-white border-b border-slate-200">
    {/* Main Header */}
    <div className="flex items-center justify-between px-6 py-3">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl leading-none">+</span>
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-sky-800 leading-none mb-1">MediCare AI <span className="bg-emerald-100 text-emerald-700 text-[10px] px-2 py-0.5 rounded-full ml-2 align-middle">CLINICAL PORTAL</span></h1>
            <p className="text-[11px] text-slate-500 font-medium">HITL Coordinator - Phòng Khám Đa Tầng Bác Sĩ Giám Sát</p>
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 pr-4 border-r border-slate-200">
          <span className="px-3 py-1.5 bg-teal-50 text-teal-700 text-xs font-bold rounded-full flex items-center gap-2 border border-teal-100">
            <div className="w-2 h-2 bg-teal-500 rounded-full animate-pulse"></div>
            Đang trực ban (Online)
          </span>
          <span className="px-3 py-1.5 bg-rose-50 text-rose-700 text-xs font-bold rounded-full flex items-center gap-2 border border-rose-100 shadow-sm">
            <Activity size={14} className="text-rose-600" />
            2 Cấp cứu
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors">
            <Bell size={20} />
            <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full border-2 border-white">3</span>
          </button>
          <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors">
            <Settings size={20} />
          </button>
          
          <div className="flex items-center gap-3 pl-2">
            <img src="https://i.pravatar.cc/150?u=dr_linh" alt="BS Linh" className="w-9 h-9 rounded-full object-cover border border-slate-200" />
            <div>
              <p className="text-sm font-bold text-slate-800 leading-tight">BS. Nguyễn Phương Linh</p>
              <p className="text-[11px] text-slate-500 font-medium">Điều phối viên trưởng HITL</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* Tabs Bar */}
    <div className="flex items-center justify-between px-6 bg-slate-50 border-t border-slate-100">
      <div className="flex gap-1">
        {['Tổng quan', 'Hàng đợi', 'Duyệt lịch hẹn'].map(tab => (
          <button key={tab} className="px-5 py-3 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors">
            {tab}
          </button>
        ))}
        <button className="px-5 py-3 text-sm font-bold text-white bg-sky-700 rounded-t-lg shadow-[0_-2px_10px_rgba(3,105,161,0.2)]">
          Quản lý lịch bác sĩ
        </button>
        {['Chat Takeover', 'Xử lý khẩn cấp'].map(tab => (
          <button key={tab} className="px-5 py-3 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors">
            {tab}
          </button>
        ))}
      </div>
      <button className="text-sm font-semibold text-sky-600 hover:text-sky-700">
        Chuyển sang Cổng Bệnh Nhân
      </button>
    </div>
  </div>
);
