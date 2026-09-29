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
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm">
      {/* ─── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-700 text-white shadow-sm">
            <Stethoscope className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-tight">
              {data.assessmentTitle}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {data.lastUpdated}
            </p>
          </div>
        </div>

        <span className="self-start sm:self-auto inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          {data.statusText}
        </span>
      </div>

      {/* ─── AI Triage Symptoms Box ────────────────────────────── */}
      <div className="mt-4 rounded-xl border border-slate-200/80 bg-slate-50/70 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-red-600">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>{data.symptoms.title}</span>
          </div>
          <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-500">
            {data.symptoms.verifiedBadge}
          </span>
        </div>
        <p className="mt-2 text-xs sm:text-sm font-medium leading-relaxed text-slate-700">
          {data.symptoms.description}
        </p>
      </div>

      {/* ─── HITL Doctor Review Box ────────────────────────────── */}
      <div className="mt-3.5 flex items-start gap-3.5 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
        <img
          src={data.doctorReview.avatarUrl}
          alt={data.doctorReview.doctorName}
          className="h-11 w-11 rounded-full border border-emerald-200 object-cover shrink-0"
        />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-bold text-slate-900">
              {data.doctorReview.doctorName}
            </span>
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
              {data.doctorReview.doctorTitle}
            </span>
          </div>
          <p className="mt-1.5 text-xs italic leading-relaxed text-slate-600">
            "{data.doctorReview.note}"
          </p>
        </div>
      </div>

      {/* ─── Card Footer ───────────────────────────────────────── */}
      <div className="mt-5 flex flex-col gap-3 pt-3 border-t border-slate-100 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>Mọi trao đổi đều được lưu trữ bảo mật theo tiêu chuẩn HIPAA & Bộ Y Tế.</span>
        </div>

        <button
          type="button"
          onClick={() => dispatch(openChat())}
          className="flex items-center justify-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-800 active:scale-95"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Mở Chatbot AI góc phải</span>
        </button>
      </div>
    </div>
  );
});
