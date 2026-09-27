import React, { memo } from 'react';
import { Phone, Ambulance, Activity, ArrowRight } from 'lucide-react';

export const ActionButtons = memo(() => (
  <div className="grid grid-cols-3 gap-4 mb-6">
    <button className="bg-red-600 hover:bg-red-700 text-white p-4 rounded-xl flex items-center justify-between transition-colors">
      <div className="flex items-center gap-3">
        <Phone className="w-8 h-8" />
        <div className="text-left">
          <div className="text-xs opacity-80 uppercase tracking-wider">Kênh liên lạc trực tiếp</div>
          <div className="font-bold text-lg">GỌI BỆNH NHÂN / NGƯỜI NHÀ</div>
          <div className="text-xs opacity-80">VoIP Hotline ưu tiên: 0912 345 678</div>
        </div>
      </div>
      <ArrowRight className="w-6 h-6" />
    </button>
    <button className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-xl flex items-center justify-between transition-colors">
      <div className="flex items-center gap-3">
        <Ambulance className="w-8 h-8" />
        <div className="text-left">
          <div className="text-xs opacity-80 uppercase tracking-wider">Hạ tầng cấp cứu lưu động</div>
          <div className="font-bold text-lg">ĐIỀU ĐỘNG CẤP CỨU 115</div>
          <div className="text-xs opacity-80">Tự động đẩy GPS + EMR sang 115 Hà Nội</div>
        </div>
      </div>
      <ArrowRight className="w-6 h-6" />
    </button>
    <button className="bg-teal-700 hover:bg-teal-800 text-white p-4 rounded-xl flex items-center justify-between transition-colors">
      <div className="flex items-center gap-3">
        <Activity className="w-8 h-8" />
        <div className="text-left">
          <div className="text-xs opacity-80 uppercase tracking-wider">Phòng can thiệp tim mạch</div>
          <div className="font-bold text-lg">BÁO ĐỘNG CATHLAB ALERT</div>
          <div className="text-xs opacity-80">Sẵn sàng kíp thông tim BV MediCare 01</div>
        </div>
      </div>
      <ArrowRight className="w-6 h-6" />
    </button>
  </div>
));
