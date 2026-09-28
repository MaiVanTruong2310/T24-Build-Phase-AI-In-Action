import React, { memo } from 'react';
import { ShieldCheck, ArrowRight } from 'lucide-react';
import { Specialty, TimeSlot, Doctor, Facility } from './types';

type Props = {
  specialty?: Specialty;
  facility?: Facility;
  doctor?: Doctor;
  slot?: TimeSlot;
  onConfirm: () => void;
};

export const SummaryPanel = memo(({ specialty, facility, doctor, slot, onConfirm }: Props) => (
  <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xl shadow-slate-200/50 sticky top-6">
    <h3 className="text-xl font-bold text-slate-900 mb-6">Tóm Tắt Đặt Lịch</h3>
    
    <div className="space-y-4 mb-6">
      <div className="flex items-center gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
        <div className="w-10 h-10 bg-sky-100 text-sky-700 rounded-full flex items-center justify-center font-bold">
          NA
        </div>
        <div>
          <div className="font-semibold text-slate-900">Nguyễn Văn An</div>
          <div className="text-xs text-slate-500">Nam, 32 tuổi • BN-100234</div>
        </div>
      </div>

      <div className="text-sm border-l-2 border-sky-500 pl-3 py-1">
        <div className="text-slate-500 mb-0.5 text-xs font-medium uppercase tracking-wider">Chuyên khoa</div>
        <div className="font-semibold text-slate-900">{specialty?.name || 'Chưa chọn'}</div>
      </div>
      
      <div className="text-sm border-l-2 border-sky-500 pl-3 py-1">
        <div className="text-slate-500 mb-0.5 text-xs font-medium uppercase tracking-wider">Cơ sở y tế</div>
        <div className="font-semibold text-slate-900">{facility?.name || 'Chưa chọn'}</div>
        {facility && <div className="text-xs text-slate-500 mt-1">{facility.address}</div>}
      </div>

      <div className="text-sm border-l-2 border-sky-500 pl-3 py-1">
        <div className="text-slate-500 mb-0.5 text-xs font-medium uppercase tracking-wider">Bác sĩ</div>
        <div className="font-semibold text-slate-900">{doctor ? `${doctor.title} ${doctor.name}` : 'Chưa chọn'}</div>
      </div>

      <div className="text-sm border-l-2 border-sky-500 pl-3 py-1">
        <div className="text-slate-500 mb-0.5 text-xs font-medium uppercase tracking-wider">Thời gian</div>
        <div className="font-semibold text-sky-700">{slot ? `${slot.time} - ${slot.date}` : 'Chưa chọn'}</div>
      </div>
    </div>

    <div className="border-t border-slate-100 pt-4 mb-6">
      <div className="flex justify-between text-sm mb-2 text-slate-600">
        <span>Phí khám lâm sàng:</span>
        <span className="font-medium">350.000 VNĐ</span>
      </div>
      <div className="flex justify-between text-sm mb-4 text-emerald-600">
        <span>BHYT chi trả (80%):</span>
        <span className="font-medium">-280.000 VNĐ</span>
      </div>
      <div className="flex justify-between items-end bg-slate-50 p-3 rounded-lg">
        <span className="font-bold text-slate-700">Tạm tính:</span>
        <span className="text-2xl font-bold text-sky-600">70.000 VNĐ</span>
      </div>
    </div>

    <div className="bg-sky-50 text-sky-800 p-3 rounded-lg text-xs mb-6 flex gap-2 leading-relaxed">
      <ShieldCheck className="w-8 h-8 shrink-0 text-sky-600" />
      <span>Thông tin đặt lịch sẽ được xác nhận bởi Hệ thống Điều phối thông minh (HITL) trong vòng 5 phút.</span>
    </div>

    <button 
      onClick={onConfirm}
      disabled={!specialty || !facility || !doctor || !slot}
      className="w-full bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95 shadow-md shadow-sky-600/20"
    >
      Xác nhận đặt lịch hẹn <ArrowRight className="w-5 h-5" />
    </button>
  </div>
));
