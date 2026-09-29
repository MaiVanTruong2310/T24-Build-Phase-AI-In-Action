import { FileText, ShieldCheck, BadgeCheck, ArrowRight, ArrowLeft, Phone, Loader2 } from 'lucide-react';

interface Props {
  specialtyName: string;
  doctorName: string;
  serviceName: string;
  date: string;
  slotTime: string;
  type: string;
  price: number;
  onBook: () => void;
  isBooking: boolean;
}

export function BookingSummary({ specialtyName, doctorName, serviceName, date, slotTime, type, price, onBook, isBooking }: Props) {
  const finalPrice = price * 0.2; // Assuming 80% BHYT coverage

  return (
    <>
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 sticky top-6 overflow-hidden">
        <div className="bg-slate-50 p-5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-600" />
            Tóm Tắt Phiếu Khám
          </h3>
          <span className="text-[10px] font-bold text-slate-500 bg-slate-200 px-2 py-1 rounded">Tự động lưu</span>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">NGƯỜI KHÁM</div>
            <div className="flex gap-3">
              <div className="w-10 h-10 bg-sky-100 text-sky-700 rounded-full flex items-center justify-center font-bold shrink-0">
                NA
              </div>
              <div>
                <div className="font-bold text-slate-900 text-sm">Hồ sơ bệnh nhân hiện tại</div>
                <div className="text-xs text-slate-500 mt-0.5">Thông tin sẽ được lấy từ hồ sơ của bạn</div>
              </div>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 mb-6">
            <div className="text-xs text-slate-600 mb-2">Triệu chứng khai báo:</div>
            <div className="text-sm font-medium text-slate-900 italic mb-3">
              "Đau thắt ngực nhẹ, khó thở khi vận động gắng sức khoảng 3 ngày nay."
            </div>
            <div className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded">
              <ShieldCheck className="w-3.5 h-3.5" /> Ưu tiên thẩm định phòng ngừa mạch vành
            </div>
          </div>

          <div className="space-y-3 mb-6">
            <div className="grid grid-cols-[100px_1fr] items-start gap-2 text-sm">
              <div className="text-slate-500">Chuyên khoa:</div>
              <div className="font-bold text-slate-900">{specialtyName || 'Chưa chọn'}</div>
            </div>
            <div className="grid grid-cols-[100px_1fr] items-start gap-2 text-sm">
              <div className="text-slate-500">Bác sĩ khám:</div>
              <div className="font-bold text-sky-700">{doctorName || 'Chưa chọn'}</div>
            </div>
            <div className="grid grid-cols-[100px_1fr] items-start gap-2 text-sm">
              <div className="text-slate-500">Dịch vụ:</div>
              <div className="font-bold text-slate-900">{serviceName || 'Chưa chọn'}</div>
            </div>
            <div className="grid grid-cols-[100px_1fr] items-start gap-2 text-sm">
              <div className="text-slate-500">Thời gian hẹn:</div>
              <div className="font-bold text-slate-900">{slotTime ? `${slotTime} - Ngày ${date}` : 'Chưa chọn'}</div>
            </div>
            <div className="grid grid-cols-[100px_1fr] items-start gap-2 text-sm">
              <div className="text-slate-500">Hình thức:</div>
              <div className="font-bold text-slate-900">{type === 'offline' ? 'Khám Trực Tiếp (P.304)' : 'Khám Video Từ Xa'}</div>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-4 mb-6">
            <div className="flex justify-between text-sm mb-2 text-slate-600">
              <span>Phí khám lâm sàng:</span>
              <span>{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price)}</span>
            </div>
            <div className="flex justify-between text-sm mb-4 text-emerald-600 font-medium">
              <span>Giảm trừ BHYT điện tử (80%):</span>
              <span>-{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price * 0.8)}</span>
            </div>
            <div className="flex justify-between items-end mt-4">
              <span className="font-bold text-slate-900">Tạm tính thanh toán:</span>
              <span className="text-2xl font-bold text-sky-700">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(finalPrice)}</span>
            </div>
          </div>

          <div className="bg-sky-50 border border-sky-100 p-3 rounded-xl text-xs text-sky-800 flex gap-3 mb-6">
            <BadgeCheck className="w-6 h-6 shrink-0 text-sky-600" />
            <span className="leading-relaxed"><strong className="font-bold">Bảo đảm chuyên môn HITL:</strong> Yêu cầu đặt lịch sẽ được chuyển ngay đến Bàn Điều Phối Y Tế duyệt và phân phòng trong vòng 15 phút.</span>
          </div>

          <button
            onClick={onBook}
            disabled={isBooking || !doctorName || !slotTime}
            className="w-full bg-sky-700 hover:bg-sky-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 transition-transform active:scale-95 shadow-md shadow-sky-700/20 mb-3"
          >
            {isBooking ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Đang xử lý...</>
            ) : (
              <>Xác nhận đặt lịch hẹn ngay <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
          <button className="w-full py-2 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors flex items-center justify-center gap-2">
            <ArrowLeft className="w-4 h-4" /> Quay lại trang tư vấn AI
          </button>
        </div>
      </div>

      <div className="mt-6 bg-red-50 border border-red-100 rounded-2xl p-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-full bg-red-100 text-red-600 flex items-center justify-center shrink-0">
          <Phone className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-900 text-sm">Cần hỗ trợ khẩn cấp?</div>
          <div className="text-xs text-slate-500">Hotline lâm sàng 24/7</div>
        </div>
        <div className="ml-auto text-lg font-bold text-red-600">
          1900 8866
        </div>
      </div>
    </>
  )
}
