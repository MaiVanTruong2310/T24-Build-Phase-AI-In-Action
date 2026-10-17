const fs = require('fs');
const path = require('path');

const write = (filePath, content) => {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filePath, content.trim());
};

const EC_DIR = 'c:/Project/Vin/Build_Phase/P-124/frontend/src/features/emergency-coordinator/components';
const AB_DIR = 'c:/Project/Vin/Build_Phase/P-124/frontend/src/features/appointment-booking/components';

// ================= Emergency Coordinator Components =================

write(`${EC_DIR}/SLATimer.tsx`, `
import React, { useState, useEffect, memo } from 'react';

export const SLATimer = memo(({ initialSeconds = 56 }: { initialSeconds?: number }) => {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, []);

  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = (seconds % 60).toString().padStart(2, '0');

  return (
    <div className="bg-white rounded-lg p-3 flex items-center gap-4">
      <div className="text-sm font-semibold text-gray-700">
        ⏱ SLA PHẢN ỨNG TỐI ĐA<br />
        <span className="text-xs text-gray-500 font-normal">Tự động kích hoạt báo động toàn viện khi hết giờ</span>
      </div>
      <div className="text-5xl font-bold text-red-600">
        {mins}:{secs}<span className="text-xl">GIÂY</span>
      </div>
    </div>
  );
});
`);

write(`${EC_DIR}/ActionButtons.tsx`, `
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
`);

write(`${EC_DIR}/TriageInfo.tsx`, `
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
      Đau thắt ngực kiểu đè nặng bóp nghẹt lan sau xương bá vai và mặt trong cánh tay trái kéo dài > 20 phút.
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
`);

write(`${EC_DIR}/ClinicalChecklist.tsx`, `
import React, { memo } from 'react';

export type Task = {
  id: string;
  title: string;
  desc: string;
};

type Props = {
  tasks: Task[];
  checked: Record<string, boolean>;
  onToggle: (id: string) => void;
};

export const ClinicalChecklist = memo(({ tasks, checked, onToggle }: Props) => (
  <div className="grid grid-cols-2 gap-3 mb-4">
    {tasks.map(t => (
      <label key={t.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 border border-transparent hover:border-gray-200 transition-colors">
        <input 
          type="checkbox" 
          className="mt-1 w-5 h-5 text-teal-600 rounded focus:ring-teal-500"
          checked={!!checked[t.id]}
          onChange={() => onToggle(t.id)}
        />
        <div>
          <div className="font-semibold text-gray-900">{t.title}</div>
          <div className="text-sm text-gray-500">{t.desc}</div>
        </div>
      </label>
    ))}
  </div>
));
`);

write(`${EC_DIR}/PatientCard.tsx`, `
import React, { memo } from 'react';

type PatientData = {
  name: string;
  age: string;
  id: string;
  phone: string;
  kin: string;
  history: string[];
};

export const PatientCard = memo(({ data }: { data: PatientData }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
    <div className="flex items-center gap-4 mb-4">
      <div className="w-14 h-14 bg-gray-200 rounded-full overflow-hidden">
        <img src="https://i.pravatar.cc/150?img=11" alt="Patient" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-gray-900">{data.name}</h2>
        <div className="text-sm text-gray-500">{data.age} • Mã: {data.id}</div>
      </div>
    </div>
    <div className="space-y-3">
      <div className="bg-gray-50 p-3 rounded-lg">
        <div className="text-xs text-gray-500 uppercase">SĐT Bệnh Nhân</div>
        <div className="font-semibold text-blue-600">{data.phone}</div>
      </div>
      <div className="bg-gray-50 p-3 rounded-lg">
        <div className="text-xs text-gray-500 uppercase">Người nhà khẩn cấp</div>
        <div className="font-semibold">{data.kin}</div>
      </div>
    </div>
  </div>
));
`);

write(`${EC_DIR}/ChatExtract.tsx`, `
import React, { memo } from 'react';
import { MessageSquare } from 'lucide-react';

export const ChatExtract = memo(() => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
    <h3 className="font-bold text-gray-800 flex items-center gap-2 mb-4">
      <MessageSquare className="w-5 h-5 text-blue-500" />
      Trích Xuất Hội Thoại Kích Hoạt
    </h3>
    <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
      <div className="flex justify-end">
        <div className="bg-blue-100 text-blue-900 p-3 rounded-2xl rounded-tr-none max-w-[80%] shadow-sm">
          Chào bác sĩ, ngực trái của tôi tự nhiên đau thắt dữ dội quá...
        </div>
      </div>
      <div className="flex justify-start">
        <div className="bg-white border border-gray-200 text-gray-800 p-3 rounded-2xl rounded-tl-none max-w-[80%] shadow-sm">
          Chào anh Long! Tình trạng đau ngực lan vai và cánh tay trái là dấu hiệu cần hết sức thận trọng...
        </div>
      </div>
    </div>
  </div>
));
`);

// ================= Appointment Booking Components =================

write(`${AB_DIR}/SpecialtyItem.tsx`, `
import React, { memo } from 'react';
import { CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import { Specialty } from './types';

type Props = {
  item: Specialty;
  isSelected: boolean;
  onSelect: (id: string) => void;
};

export const SpecialtyItem = memo(({ item, isSelected, onSelect }: Props) => {
  const Icon = item.icon;
  return (
    <button
      onClick={() => onSelect(item.id)}
      className={clsx(
        "w-full text-left p-4 rounded-xl border flex items-center justify-between transition-all",
        isSelected ? "border-teal-600 bg-teal-50 shadow-sm" : "border-gray-200 bg-white hover:border-teal-300 hover:bg-gray-50"
      )}
    >
      <div className="flex items-center gap-4">
        <div className={clsx("p-3 rounded-lg", isSelected ? "bg-teal-600 text-white" : "bg-gray-100 text-gray-500")}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h4 className={clsx("font-semibold text-lg", isSelected ? "text-teal-900" : "text-gray-800")}>{item.name}</h4>
          <p className={clsx("text-sm", isSelected ? "text-teal-700" : "text-gray-500")}>{item.desc}</p>
        </div>
      </div>
      {isSelected && <CheckCircle2 className="w-6 h-6 text-teal-600" />}
    </button>
  );
});
`);

write(`${AB_DIR}/SlotItem.tsx`, `
import React, { memo } from 'react';
import clsx from 'clsx';
import { TimeSlot } from './types';

type Props = {
  slot: TimeSlot;
  isSelected: boolean;
  onSelect: (id: string) => void;
};

export const SlotItem = memo(({ slot, isSelected, onSelect }: Props) => {
  const disabled = slot.status === 'booked';
  return (
    <button
      disabled={disabled}
      onClick={() => onSelect(slot.id)}
      className={clsx(
        "p-3 rounded-lg border text-center transition-all relative overflow-hidden",
        disabled && "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed opacity-60",
        isSelected && "bg-teal-700 border-teal-700 text-white shadow-md transform scale-[1.02]",
        !disabled && !isSelected && "bg-white border-teal-100 text-gray-700 hover:border-teal-500 hover:shadow-sm"
      )}
    >
      {isSelected && <div className="absolute top-0 right-0 w-4 h-4 bg-teal-500 rounded-bl-lg" />}
      <div className="font-bold text-lg">{slot.time}</div>
      <div className="text-xs mt-1">
        {disabled ? 'Đã kín lịch' : isSelected ? 'Đang chọn' : 'Trống chỗ'}
      </div>
    </button>
  );
});
`);

write(`${AB_DIR}/SummaryPanel.tsx`, `
import React, { memo } from 'react';
import { ShieldCheck, ArrowRight } from 'lucide-react';
import { Specialty, TimeSlot } from './types';

type Props = {
  specialty?: Specialty;
  slot?: TimeSlot;
  onConfirm: () => void;
};

export const SummaryPanel = memo(({ specialty, slot, onConfirm }: Props) => (
  <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-lg sticky top-6">
    <h3 className="text-xl font-bold text-gray-900 mb-6">Tóm Tắt Phiếu Khám</h3>
    
    <div className="space-y-4 mb-6">
      <div className="flex items-center gap-3 bg-gray-50 p-3 rounded-lg">
        <div className="w-10 h-10 bg-teal-100 text-teal-800 rounded-full flex items-center justify-center font-bold">
          VA
        </div>
        <div>
          <div className="font-semibold">Vũ Anh</div>
          <div className="text-xs text-gray-500">Nam, 42 tuổi • GD-4-79-11</div>
        </div>
      </div>

      <div className="text-sm">
        <div className="text-gray-500 mb-1">Chuyên khoa:</div>
        <div className="font-semibold">{specialty?.name || 'Chưa chọn'}</div>
      </div>
      
      <div className="text-sm">
        <div className="text-gray-500 mb-1">Thời gian hẹn:</div>
        <div className="font-semibold text-teal-700">{slot ? \`\${slot.time} - Thứ Tư, 24/10/2023\` : 'Chưa chọn'}</div>
      </div>
    </div>

    <div className="border-t border-gray-100 pt-4 mb-6">
      <div className="flex justify-between text-sm mb-2 text-gray-600">
        <span>Phí khám lâm sàng:</span>
        <span>350.000 VNĐ</span>
      </div>
      <div className="flex justify-between text-sm mb-4 text-teal-600">
        <span>Giảm trừ BHYT (80%):</span>
        <span>-280.000 VNĐ</span>
      </div>
      <div className="flex justify-between items-end">
        <span className="font-semibold text-gray-700">Tạm tính thanh toán:</span>
        <span className="text-2xl font-bold text-teal-700">70.000 VNĐ</span>
      </div>
    </div>

    <div className="bg-blue-50 text-blue-800 p-3 rounded-lg text-xs mb-6 flex gap-2 leading-relaxed">
      <ShieldCheck className="w-8 h-8 shrink-0 text-blue-600" />
      <span>Bảo đảm chuyên môn HITL: Yêu cầu đặt lịch sẽ được duyệt trong vòng 15 phút.</span>
    </div>

    <button 
      onClick={onConfirm}
      className="w-full bg-teal-700 hover:bg-teal-800 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-transform active:scale-95 shadow-md"
    >
      Xác nhận đặt lịch hẹn <ArrowRight className="w-5 h-5" />
    </button>
  </div>
));
`);

write(`${AB_DIR}/types.ts`, `
import React from 'react';
export type Specialty = { id: string; name: string; desc: string; icon: React.ElementType };
export type TimeSlot = { id: string; time: string; status: 'available' | 'booked' | 'selected' };
`);

console.log('Components extracted.');
