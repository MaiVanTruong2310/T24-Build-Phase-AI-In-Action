import { Send, MessageSquare } from 'lucide-react';

export function Notification() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
            <Send size={16} />
          </div>
          <h2 className="text-base font-bold text-slate-800">Thông Báo Tự Động Tới Bệnh Nhân</h2>
        </div>
        <div className="text-[10px] font-bold text-slate-500 uppercase">
          SMS + App Notification
        </div>
      </div>

      <p className="text-xs text-slate-500 mb-2">Nội dung gửi bệnh nhân ngay khi Điều phối viên bấm "Phê Duyệt Lịch Ngay":</p>

      <div className="bg-white border border-slate-200 rounded-xl p-4 mb-3 relative">
        <div className="absolute -left-2 top-4 w-4 h-4 bg-white border-t border-l border-slate-200 transform -rotate-45"></div>
        <p className="text-sm text-slate-700 leading-relaxed relative z-10">
          Lịch hẹn đã được ĐPV BS. Nguyễn Phương Linh phê duyệt. Vui lòng đến trước 10 phút tại Phòng 304 để đo điện tâm đồ sơ bộ và hoàn tất thủ tục BHYT.
        </p>
      </div>

      <div className="flex justify-between items-center text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-4 rounded bg-blue-500 flex items-center justify-center">
            <MessageSquare size={10} className="text-white" />
          </div>
          Đồng bộ qua Zalo OA Bệnh Viện
        </div>
        <div>
          Ký số điện tử: MD-BS-LINH-9921
        </div>
      </div>
    </div>
  );
}
