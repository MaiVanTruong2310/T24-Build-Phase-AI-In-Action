import { Stethoscope } from 'lucide-react';
import { AITriageData } from '../types';

interface AITriageCardProps {
  triage: AITriageData;
}

export function AITriageCard({ triage }: AITriageCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-sky-50 text-sky-600 flex items-center justify-center">
            <Stethoscope size={15} />
          </div>
          <h3 className="text-xs font-bold text-slate-800 tracking-wide uppercase">
            Suy Luận AI Triage
          </h3>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
          Tin cậy {triage.confidence}%
        </span>
      </div>

      {/* Differential Diagnosis */}
      <div>
        <p className="text-[11px] text-slate-500 font-medium">Chẩn đoán phân biệt:</p>
        <p className="text-xs font-black text-slate-900 leading-snug mt-0.5">
          {triage.differentialDiagnosis}
        </p>
      </div>

      {/* Risk Factors */}
      <div>
        <p className="text-[11px] text-slate-500 font-medium mb-1.5">Yếu tố cấu thành nguy cơ:</p>
        <div className="flex flex-wrap gap-1.5">
          {triage.riskFactors.map((factor, index) => (
            <span
              key={index}
              className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-semibold border border-slate-200"
            >
              {factor}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
