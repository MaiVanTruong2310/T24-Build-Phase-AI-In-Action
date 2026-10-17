import { TypewriterLoader } from '../../../components/TypewriterLoader';
import { XCircle, CalendarClock, CheckCircle2, ArrowRightLeft } from 'lucide-react';

interface HeaderProps {
  onApprove?: () => void;
  onReject?: () => void;
  isLoading?: boolean;
}

export function Header({ onApprove, onReject, isLoading }: HeaderProps) {
  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded-full uppercase tracking-wide">
            HITL VERIFICATION ENGINE
          </span>
          <span className="text-sm font-semibold text-slate-500">
            Phiên đối chiếu lâm sàng #MED-8942-VN
          </span>
        </div>
        
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-amber-500"></div>
          <span className="text-sm font-bold text-amber-600">Chờ điều phối viên xác nhận</span>
        </div>
        
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          Thẩm Định & Duyệt Lịch Hẹn Khám Bệnh
        </h1>
        
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <ArrowRightLeft size={16} className="text-emerald-500" />
          <span>Liên kết trực tiếp với Cổng Bệnh Nhân VCare+ CareConnect • Cập nhật thời gian thực (Socket Active)</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button 
          onClick={onReject}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 border-2 border-rose-100 text-rose-600 font-bold rounded-xl hover:bg-rose-50 transition-colors disabled:opacity-50">
          <XCircle size={18} />
          Từ Chối & Nêu Lý Do
        </button>
        <button 
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 border-2 border-sky-100 text-sky-700 font-bold rounded-xl hover:bg-sky-50 transition-colors disabled:opacity-50">
          <CalendarClock size={18} />
          Đề Xuất Đổi Giờ / Bác Sĩ
        </button>
        <button 
          onClick={onApprove}
          disabled={isLoading}
          className="flex items-center gap-2 px-5 py-2 bg-teal-600 text-white font-bold rounded-xl hover:bg-teal-700 transition-colors shadow-sm disabled:opacity-50">
          {isLoading ? <TypewriterLoader /> : <CheckCircle2 size={18} />}
          Phê Duyệt Lịch Ngay
        </button>
      </div>
    </div>
  );
}
