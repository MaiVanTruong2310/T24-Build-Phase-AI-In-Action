import React, { memo } from 'react';
import { ShieldAlert } from 'lucide-react';

export const TriageInfo = memo(() => (
  <div className="bg-red-50 border border-red-100 rounded-xl p-5 mb-6">
    <div className="flex justify-between items-center mb-4">
      <div className="flex items-center gap-2 text-red-600 font-bold">
        <ShieldAlert className="w-5 h-5" />
        <span>PHÂN TÍCH CHẨN ĐOÁN SƠ BỘ</span>
      </div>
      <span className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold">⚠️ ĐỘ TIN CẬY AI: 96.8%</span>
    </div>
    <h3 className="text-2xl font-bold text-gray-900 mb-2">
      Nghi ngờ Nhồi Máu Cơ Tim Cấp (Acute Myocardial Infarction / STEMI)
    </h3>
    <p className="text-gray-700">
      Đau thắt ngực kiểu đè nặng bóp nghẹt lan sau xương bá vai và mặt trong cánh tay trái kéo dài {'>'} 20 phút.
      Vã mồ hôi lạnh toàn thân kèm khó thở gắng sức, không thuyên giảm khi nghỉ ngơi.
    </p>
    
    <div className="grid grid-cols-3 gap-4 mt-6">
      <div className="bg-white p-4 rounded-lg border border-red-100">
        <div className="text-sm text-gray-500 mb-1">Huyết áp (BP)</div>
        <div className="text-3xl font-bold text-red-600">145/95 <span className="text-sm font-normal text-gray-500">mmHg</span></div>
      </div>
      <div className="bg-white p-4 rounded-lg border border-red-100">
        <div className="text-sm text-gray-500 mb-1">Nhịp tim (Heart Rate)</div>
        <div className="text-3xl font-bold text-red-600">102 <span className="text-sm font-normal text-gray-500">bpm</span></div>
      </div>
      <div className="bg-white p-4 rounded-lg border border-red-100">
        <div className="text-sm text-gray-500 mb-1">Nồng độ Oxy (SpO2)</div>
        <div className="text-3xl font-bold text-red-600">94 <span className="text-sm font-normal text-gray-500">%</span></div>
      </div>
    </div>
  </div>
));
