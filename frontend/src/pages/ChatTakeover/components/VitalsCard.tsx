import { Activity } from 'lucide-react';
import { VitalsData } from '../types';

interface VitalsCardProps {
  vitals: VitalsData;
}

export function VitalsCard({ vitals }: VitalsCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-rose-50 text-rose-600 flex items-center justify-center">
            <Activity size={15} />
          </div>
          <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase">
            Sinh Tốn Đồng Bộ Real-time
          </h3>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          Apple Health
        </span>
      </div>

      {/* 3 Metric Badges */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-2 text-center">
          <p className="text-[10px] text-slate-500 font-semibold uppercase">Huyết áp</p>
          <p className="text-sm font-black text-rose-600 leading-tight mt-0.5">{vitals.bloodPressure}</p>
          <p className="text-[10px] text-rose-600 font-semibold">mmHg ({vitals.bloodPressureStatus})</p>
        </div>

        <div className="bg-slate-50 border border-slate-100 rounded-xl p-2 text-center">
          <p className="text-[10px] text-slate-500 font-semibold uppercase">Nhịp tim</p>
          <p className="text-sm font-black text-sky-700 leading-tight mt-0.5">{vitals.heartRate}</p>
          <p className="text-[10px] text-slate-500 font-medium">bpm</p>
        </div>

        <div className="bg-slate-50 border border-slate-100 rounded-xl p-2 text-center">
          <p className="text-[10px] text-slate-500 font-semibold uppercase">SpO2</p>
          <p className="text-sm font-black text-emerald-600 leading-tight mt-0.5">{vitals.spO2}%</p>
          <p className="text-[10px] text-emerald-600 font-medium">{vitals.spO2Status}</p>
        </div>
      </div>

      {/* ECG Lead II Preview */}
      <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3 space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-600 font-medium">{vitals.ecgLead}</span>
          <span className="text-rose-600 font-bold">{vitals.ecgStatus}</span>
        </div>

        {/* Realistic ECG waveform in SVG */}
        <div className="h-10 w-full flex items-center justify-center overflow-hidden">
          <svg
            className="w-full h-8 text-rose-500"
            viewBox="0 0 300 40"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M 0 20 L 35 20 L 40 22 L 45 18 L 50 20 L 70 20 L 75 14 L 80 20 L 95 20 L 100 24 L 105 -5 L 112 36 L 118 12 L 126 12 L 132 20 L 155 20 L 160 22 L 165 18 L 170 20 L 190 20 L 195 14 L 200 20 L 215 20 L 220 24 L 225 -5 L 232 36 L 238 12 L 246 12 L 252 20 L 300 20"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
