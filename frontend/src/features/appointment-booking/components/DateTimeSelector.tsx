import { CalendarIcon, Building2, Video, Check, MapPin, ArrowRightLeft } from 'lucide-react';
import clsx from 'clsx';
import { Facility, Schedule } from '../api';

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

type AppointmentType = 'offline' | 'telehealth';

interface Props {
  selectedDate: string;
  onSelectDate: (d: string) => void;
  selectedType: AppointmentType;
  onSelectType: (t: AppointmentType) => void;
  selectedSlot: string;
  onSelectSlot: (s: string) => void;
  schedules?: Schedule[];
  selectedFacility?: Facility;
}

export function DateTimeSelector({ selectedDate, onSelectDate, selectedType, onSelectType, selectedSlot, onSelectSlot, schedules, selectedFacility }: Props) {
  const availableSchedules = schedules || [];
  const morningSlots = availableSchedules.filter(s => {
    const hour = new Date(s.starts_at).getHours();
    return hour < 12;
  }).map(s => ({
    id: s.id,
    time: new Date(s.starts_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    status: s.status === 'available' ? 'available' : 'booked',
    slots: s.capacity
  }));

  const afternoonSlots = availableSchedules.filter(s => {
    const hour = new Date(s.starts_at).getHours();
    return hour >= 12;
  }).map(s => ({
    id: s.id,
    time: new Date(s.starts_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    status: s.status === 'available' ? 'available' : 'booked',
    slots: s.capacity
  }));

  const dateOptions = Array.from({ length: 5 }, (_, index) => {
    const value = new Date();
    value.setHours(0, 0, 0, 0);
    value.setDate(value.getDate() + index);
    return {
      value: formatLocalDate(value),
      day: value.toLocaleDateString('vi-VN', { weekday: 'short' }).replace('.', ''),
      label: value.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }),
    };
  });

  return (
    <>
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-bold text-slate-900 text-lg flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-sky-500"></div>
            3. Chọn Ngày & Khung Giờ
          </h2>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-sky-600">
            <CalendarIcon className="w-4 h-4" /> Lịch trống theo ngày
          </div>
        </div>

        {/* Date Carousel */}
        <div className="flex gap-2 mb-6">
          {dateOptions.map((dateOption, idx) => {
            const isSelected = dateOption.value === selectedDate;
            return (
              <div 
                key={dateOption.value}
                onClick={() => onSelectDate(dateOption.value)}
                className={clsx(
                  "flex-1 py-3 text-center rounded-2xl cursor-pointer border transition-all duration-200 relative",
                  isSelected 
                    ? "bg-sky-700 text-white border-sky-700 shadow-md" 
                    : "bg-slate-50 text-slate-600 border-transparent hover:border-sky-200"
                )}
              >
                <div className={clsx("text-xs font-semibold mb-0.5", isSelected ? "text-sky-100" : "text-slate-500")}>
                  {idx === 0 ? 'Hôm nay' : dateOption.day}
                </div>
                <div className="text-xl font-bold">{dateOption.label}</div>
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
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {morningSlots.map(slot => {
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
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {afternoonSlots.map(slot => {
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
              {selectedFacility ? `${selectedFacility.name}${selectedFacility.address ? ` — ${selectedFacility.address}` : ''}` : 'Chọn cơ sở để xem địa điểm khám.'}
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

