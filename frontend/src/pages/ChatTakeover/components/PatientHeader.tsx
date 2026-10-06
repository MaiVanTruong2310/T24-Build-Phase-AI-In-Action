import { UserCheck, Video, CalendarPlus, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { PatientQueueItem } from '../types';

interface PatientHeaderProps {
  patient: PatientQueueItem;
  isTakenOver: boolean;
  onToggleTakeover: () => void;
  onResolve: () => void;
  onEscalate: () => void;
  onVideoCall: () => void;
  onQuickAppointment: () => void;
}

export function PatientHeader({
  patient,
  isTakenOver,
  onToggleTakeover,
  onResolve,
  onEscalate,
  onVideoCall,
  onQuickAppointment,
}: PatientHeaderProps) {
  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 p-4 shadow-xs">
      {/* Top Patient Summary & Takeover Switch */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="relative shrink-0">
            {patient.avatar ? (
              <img
                src={patient.avatar}
                alt={patient.name}
                className="w-12 h-12 rounded-full object-cover border-2 border-slate-200 shadow-xs"
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-slate-200 text-slate-700 font-bold flex items-center justify-center">
                {patient.name.charAt(0)}
              </div>
            )}
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-600 text-white rounded-full flex items-center justify-center text-[10px] font-bold border-2 border-white shadow-xs">
              !
            </span>
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-black text-slate-900 leading-tight whitespace-nowrap">{patient.name}</h2>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 whitespace-nowrap">
                {patient.age} tuổi
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 whitespace-nowrap">
                {patient.gender}
              </span>
              <span className="text-xs font-extrabold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 whitespace-nowrap">
                Nguy cơ Tim mạch: {patient.riskLevel}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
              <span className="whitespace-nowrap">
                Mã BN: <strong className="font-semibold text-slate-800">{patient.code}</strong>
              </span>
              <span className="whitespace-nowrap">
                Tiền sử:{' '}
                <strong className="font-semibold text-rose-600">
                  {patient.medicalHistory.join(', ') || 'Chưa ghi nhận'}
                </strong>
              </span>
              <span className="whitespace-nowrap">
                Dị ứng:{' '}
                <strong className="font-semibold text-slate-700">
                  {patient.allergies.join(', ') || 'Không có'}
                </strong>
              </span>
            </div>
          </div>
        </div>

        {/* Takeover Control Group */}
        <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3 shrink-0">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-bold">
            <button
              onClick={() => isTakenOver && onToggleTakeover()}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                !isTakenOver
                  ? 'bg-white text-slate-800 shadow-2xs font-extrabold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              🤖 AI Tự động
            </button>
            <button
              onClick={() => !isTakenOver && onToggleTakeover()}
              className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                isTakenOver
                  ? 'bg-teal-600 text-white shadow-2xs font-extrabold'
                  : 'text-teal-700 hover:text-teal-900'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isTakenOver ? 'bg-white' : 'bg-teal-500 animate-pulse'}`}></span>
              Bác sĩ trực tiếp
            </button>
          </div>

          <button
            onClick={onToggleTakeover}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-extrabold text-xs tracking-wider transition-all shadow-sm ${
              isTakenOver
                ? 'bg-slate-800 hover:bg-slate-900 text-white'
                : 'bg-sky-700 hover:bg-sky-800 text-white active:scale-98'
            }`}
          >
            <UserCheck size={16} />
            {isTakenOver ? 'TRẢ VỀ AI TỰ ĐỘNG' : 'TIẾP QUẢN TRÒ CHUYỆN (TAKE OVER)'}
          </button>
          {isTakenOver && (
            <button
              onClick={onResolve}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-extrabold tracking-wider text-white shadow-sm transition-all hover:bg-emerald-700"
            >
              <CheckCircle2 size={16} />
              ĐÁNH DẤU ĐÃ XỬ LÝ
            </button>
          )}
        </div>
      </div>

      {/* Action Buttons & Compliance Note */}
      <div className="pt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={onEscalate}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-700 hover:bg-rose-800 text-white text-xs font-bold rounded-xl shadow-2xs transition-colors"
          >
            <ShieldAlert size={14} />
            Chuyển sang Ca Escalation Cấp cứu
          </button>

          <button
            onClick={onVideoCall}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-sky-200 bg-sky-50 hover:bg-sky-100 text-sky-700 text-xs font-bold rounded-xl transition-colors"
          >
            <Video size={14} />
            Gọi Video Khám Sơ Bộ
          </button>

          <button
            onClick={onQuickAppointment}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-teal-200 bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-bold rounded-xl transition-colors"
          >
            <CalendarPlus size={14} />
            Tạo Lịch Khám Nhanh (Ưu tiên)
          </button>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <CheckCircle2 size={14} className="text-teal-600" />
          <span>Ghi log can thiệp HITL theo HIPAA</span>
        </div>
      </div>
    </div>
  );
}
