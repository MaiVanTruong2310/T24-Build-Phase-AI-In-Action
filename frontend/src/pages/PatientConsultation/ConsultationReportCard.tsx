import { memo } from 'react';
import { Stethoscope, AlertCircle, ShieldCheck, MessageSquare } from 'lucide-react';
import { useDispatch } from 'react-redux';
import { openChat } from '../../app/store';
import type { ConsultationData } from './types';

interface Props {
  data: ConsultationData;
}

export const ConsultationReportCard = memo(function ConsultationReportCard({ data }: Props) {
  const dispatch = useDispatch();

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/65 backdrop-blur-md p-5 sm:p-6 shadow-xl text-slate-100">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/30 text-cyan-400">
            <Stethoscope className="h-5 w-5" strokeWidth={2.2} />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-slate-100 leading-tight">
              {data.assessmentTitle}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Cập nhật gần nhất: {data.lastUpdated}
            </p>
          </div>
        </div>

        <span className="self-start sm:self-auto inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-950/40 px-3 py-1 text-xs font-medium text-amber-300">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
          {data.statusText}
        </span>
      </div>

      {/* ─── AI Triage Symptoms Box ────────────────────────────── */}
      <div className="mt-5 rounded-xl border border-slate-800/90 bg-slate-950/60 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span>{data.symptoms.title}</span>
          </div>
          <span className="rounded-md border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-300">
            {data.symptoms.verifiedBadge}
          </span>
        </div>
        <p className="mt-2.5 text-xs sm:text-sm font-normal leading-relaxed text-slate-300">
          {data.symptoms.description}
        </p>
      </div>

      {/* ─── HITL Doctor Review Box ────────────────────────────── */}
      <div className="mt-4 flex items-start gap-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-4">
        <img
          src={data.doctorReview.avatarUrl}
          alt={data.doctorReview.doctorName}
          className="h-11 w-11 rounded-xl border border-emerald-500/40 object-cover shrink-0"
        />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-100">
              {data.doctorReview.doctorName}
            </span>
            <span className="rounded-md border border-emerald-500/30 bg-emerald-950/60 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
              {data.doctorReview.doctorTitle}
            </span>
          </div>
          <p className="mt-1.5 text-xs italic leading-relaxed text-slate-300">
            "{data.doctorReview.note}"
          </p>
        </div>
      </div>

      {/* ─── Card Footer ───────────────────────────────────────── */}
      <div className="mt-6 flex flex-col gap-3 pt-4 border-t border-slate-800/80 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>Hồ sơ lâm sàng mã hóa bảo mật theo chuẩn HIPAA & Bộ Y Tế.</span>
        </div>

        <button
          type="button"
          onClick={() => dispatch(openChat())}
          className="btn-clinical-primary px-4 py-2.5 rounded-xl text-xs flex items-center justify-center gap-2"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Trao Đổi Trực Tiếp Với Bác Sĩ</span>
        </button>
      </div>
    </div>
  );
});

