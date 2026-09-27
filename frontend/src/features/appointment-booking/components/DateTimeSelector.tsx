import { CalendarIcon, Building2, Video, Check, MapPin, ArrowRightLeft } from 'lucide-react';
import clsx from 'clsx';

const MORNING_SLOTS = [
  { id: 'm1', time: '08:00', status: 'available', slots: 1 },
  { id: 'm2', time: '08:45', status: 'available', slots: 2 },
  { id: 'm3', time: '09:30', status: 'booked', slots: 0 },
  { id: 'm4', time: '10:15', status: 'available', slots: 1 },
];

const AFTERNOON_SLOTS = [
  { id: 'a1', time: '13:30', status: 'available', slots: 3 },
  { id: 'a2', time: '14:15', status: 'available', slots: 2 },
  { id: 'a3', time: '15:00', status: 'available', slots: 2 },
  { id: 'a4', time: '16:00', status: 'available', slots: 1 },
];

interface Props {
  selectedDate: string;
  onSelectDate: (d: string) => void;
  selectedType: string;
  onSelectType: (t: string) => void;
  selectedSlot: string;
  onSelectSlot: (s: string) => void;
}

export function DateTimeSelector({ selectedDate, onSelectDate, selectedType, onSelectType, selectedSlot, onSelectSlot }: Props) {
  return (
    <>
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-bold text-slate-900 text-lg flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-sky-500"></div>
            3. Chọn Ngày & Khung Giờ
          </h2>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-sky-600 cursor-pointer hover:text-sky-700">
            <CalendarIcon className="w-4 h-4" /> Tháng 10, 2023
          </div>
        </div>

        {/* Date Carousel */}
        <div className="flex gap-2 mb-6">
          {['22', '23', '24', '25', '26'].map((day, idx) => {
            const isSelected = day === selectedDate;
            const daysOfWeek = ['T2', 'T3', 'Hôm nay', 'T5', 'T6'];
            return (
              <div 
                key={day}
                onClick={() => onSelectDate(day)}
                className={clsx(
                  "flex-1 py-3 text-center rounded-2xl cursor-pointer border transition-all duration-200 relative",
                  isSelected 
                    ? "bg-sky-700 text-white border-sky-700 shadow-md" 
                    : "bg-slate-50 text-slate-600 border-transparent hover:border-sky-200"
                )}
              >
                <div className={clsx("text-xs font-semibold mb-0.5", isSelected ? "text-sky-100" : "text-slate-500")}>
                  {daysOfWeek[idx]}
                </div>
                <div className="text-xl font-bold">{day}</div>
                {idx === 2 && !isSelected && (
                  <div className="text-[9px] font-bold text-sky-600 uppercase mt-0.5">Thứ 4</div>
                )}
                {isSelected && (
                  <div className="text-[9px] font-bold text-sky-200 uppercase mt-0.5">Thứ 4</div>
                )}
                {/* Indicator dot */}
                {!isSelected && (
                  <div className={clsx("w-1.5 h-1.5 rounded-full mx-auto mt-1", idx === 0 ? "bg-red-400" : "bg-emerald-400")}></div>
                )}
              </div>
            );
          })}
        </div>

        {/* Form of Visit */}
        <div className="flex gap-3 mb-8">
          <button 
            onClick={() => onSelectType('offline')}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all font-semibold text-sm",
              selectedType === 'offline' 
                ? "bg-sky-50 border-sky-200 text-sky-700" 
                : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
            )}
          >
            <Building2 className="w-4 h-4" /> Tại Phòng Khám (P. 304 Tầng 3)
          </button>
          <button 
            onClick={() => onSelectType('telehealth')}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all font-semibold text-sm",
              selectedType === 'telehealth' 
                ? "bg-sky-50 border-sky-200 text-sky-700" 
                : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
            )}
          >
            <Video className="w-4 h-4" /> Khám Video Từ Xa (Telehealth)
          </button>
        </div>

        {/* Time Slots */}
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-700 flex items-center gap-2">
                <span className="text-amber-500 text-lg">☀️</span> Buổi Sáng
              </h3>
              <span className="text-xs font-medium text-slate-400">Giờ làm việc: 08:00 - 11:30</span>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {MORNING_SLOTS.map(slot => {
                const isSelected = selectedSlot === slot.id;
                const isBooked = slot.status === 'booked';
                return (
                  <button
                    key={slot.id}
                    disabled={isBooked}
                    onClick={() => onSelectSlot(slot.id)}
                    className={clsx(
                      "py-2.5 rounded-xl border text-center transition-all relative overflow-hidden flex flex-col items-center justify-center",
                      isBooked ? "bg-slate-50 border-slate-100 text-slate-400 cursor-not-allowed" :
                      isSelected ? "bg-sky-700 border-sky-700 text-white shadow-md transform scale-105" :
                      "bg-sky-50/50 border-sky-100 text-sky-900 hover:border-sky-300 hover:bg-sky-50"
                    )}
                  >
                    {isSelected && <div className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-400 border border-white"></div>}
                    <div className="font-bold">{slot.time}</div>
                    <div className={clsx("text-[10px] font-medium mt-0.5", isBooked ? "text-red-400" : isSelected ? "text-sky-200" : "text-sky-600")}>
                      {isBooked ? 'Đã kín lịch' : isSelected ? 'Đang chọn' : `Trống ${slot.slots} chỗ`}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-700 flex items-center gap-2">
                <span className="text-sky-500 text-lg">⛅</span> Buổi Chiều
              </h3>
              <span className="text-xs font-medium text-slate-400">Giờ làm việc: 13:30 - 17:00</span>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {AFTERNOON_SLOTS.map(slot => {
                const isSelected = selectedSlot === slot.id;
                const isBooked = slot.status === 'booked';
                return (
                  <button
                    key={slot.id}
                    disabled={isBooked}
                    onClick={() => onSelectSlot(slot.id)}
                    className={clsx(
                      "py-2.5 rounded-xl border text-center transition-all relative overflow-hidden flex flex-col items-center justify-center",
                      isBooked ? "bg-slate-50 border-slate-100 text-slate-400 cursor-not-allowed" :
                      isSelected ? "bg-sky-700 border-sky-700 text-white shadow-md transform scale-105" :
                      "bg-sky-50/50 border-sky-100 text-sky-900 hover:border-sky-300 hover:bg-sky-50"
                    )}
                  >
                    {isSelected && <div className="absolute -top-1 -right-1 w-6 h-6 bg-emerald-500 rotate-45 transform translate-x-1/2 -translate-y-1/2"></div>}
                    {isSelected && <Check className="absolute top-0.5 right-0.5 w-2.5 h-2.5 text-white z-10" />}
                    <div className="font-bold">{slot.time}</div>
                    <div className={clsx("text-[10px] font-medium mt-0.5", isBooked ? "text-red-400" : isSelected ? "text-sky-200" : "text-sky-600")}>
                      {isBooked ? 'Đã kín lịch' : isSelected ? 'Đang chọn' : `Trống ${slot.slots} chỗ`}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-50 rounded-2xl border border-slate-200 p-4">
        <div className="flex gap-3">
          <div className="w-8 h-8 rounded-full bg-sky-100 text-sky-600 flex items-center justify-center shrink-0">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-slate-900 text-sm mb-1">Địa điểm khám lâm sàng</h4>
            <p className="text-sm text-slate-600 mb-2">
              Khu Khám Chuyên Sâu, Phòng 304 - Tầng 3, MediCare AI Central Tower, 120 Hai Bà Trưng, Q.1, TP.HCM
            </p>
            <a href="#" className="text-xs font-semibold text-sky-600 hover:underline flex items-center gap-1">
              <ArrowRightLeft className="w-3 h-3" /> Chỉ dẫn vị trí & Hướng dẫn gửi xe tự động gửi qua SMS
            </a>
          </div>
        </div>
      </div>
    </>
  )
}
