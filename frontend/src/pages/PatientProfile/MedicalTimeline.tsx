import { memo } from 'react';
import {
  Clock,
  User,
  FileText,
  Pill,
  Image,
  BarChart3,
  ExternalLink,
  MessageSquare,
  CalendarPlus,
  Shield,
  Download,
  Search,
  Filter,
} from 'lucide-react';
import type { TimelineEntry } from './types';

interface MedicalTimelineProps {
  entries: TimelineEntry[];
}

/* ─── Badge color mapping ───────────────────────────────────────── */
const BADGE_STYLES: Record<string, string> = {
  teal: 'bg-teal-50 text-teal-700 ring-1 ring-inset ring-teal-200/60',
  blue: 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200/60',
  amber: 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200/60',
};

const DOT_STYLES: Record<string, string> = {
  teal: 'bg-teal-500 ring-teal-200',
  blue: 'bg-sky-500 ring-sky-200',
  amber: 'bg-amber-500 ring-amber-200',
};

export const MedicalTimeline = memo(function MedicalTimeline({
  entries,
}: MedicalTimelineProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Section header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
        <div>
          <h3 className="text-[15px] font-bold text-slate-800">
            Dòng thời gian y khoa tương tác
          </h3>
          <p className="mt-0.5 text-[11px] text-slate-400">
            Lịch sử toàn bộ chứng thực điện tử và phê duyệt của các bác sĩ đã
            phê HITL
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Bộ lọc chuyên khoa"
              className="w-36 rounded-md border border-slate-200 bg-slate-50 py-1.5 pl-7 pr-2 text-[11px] text-slate-600 placeholder:text-slate-400 focus:border-[#0e7490] focus:outline-none focus:ring-1 focus:ring-[#0e7490]/30"
            />
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-slate-500 transition hover:bg-slate-50"
          >
            <Filter className="h-3 w-3" />
            Tất cả chuyên khoa Show
          </button>
        </div>
      </div>

      {/* Timeline entries */}
      <div className="relative px-5 py-5">
        {/* Vertical connector line */}
        <div className="absolute bottom-0 left-[31px] top-0 w-px bg-slate-200" />

        <div className="space-y-6">
          {entries.map((entry) => (
            <TimelineEntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      </div>
    </section>
  );
});

/* ─── Individual Timeline Entry ─────────────────────────────────── */
function TimelineEntryCard({ entry }: { entry: TimelineEntry }) {
  return (
    <div className="relative flex gap-4">
      {/* Timeline dot */}
      <div
        className={`relative z-10 mt-1.5 h-3 w-3 shrink-0 rounded-full ring-[3px] ${DOT_STYLES[entry.badgeColor]}`}
      />

      {/* Content card */}
      <div className="min-w-0 flex-1 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
        {/* Card header */}
        <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span
                className={`rounded px-2 py-px text-[10px] font-bold ${BADGE_STYLES[entry.badgeColor]}`}
              >
                {entry.badgeLabel}
              </span>
              <h4 className="text-[13px] font-bold text-slate-800">
                {entry.title}
              </h4>
              <span className="text-[11px] text-slate-400">
                • {entry.date} {entry.time && `lúc ${entry.time}`}
              </span>
            </div>

            {entry.hitlBadge && (
              <div className="mt-1.5 inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200/60">
                <Shield className="h-2.5 w-2.5" />
                {entry.hitlBadge}
              </div>
            )}
          </div>
        </div>

        {/* Doctor info */}
        <div className="flex items-center gap-2.5 border-b border-slate-100 px-4 py-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-slate-400">
            <User className="h-3.5 w-3.5" />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-slate-700">
              {entry.doctorName}
            </p>
            <p className="text-[11px] text-slate-400">
              {entry.doctorDepartment}
            </p>
          </div>
        </div>

        {/* Body — Findings */}
        {entry.findings && entry.findings.length > 0 && (
          <div className="px-4 py-3">
            {entry.findings.map((finding, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#0e7490]" />
                <div>
                  <p className="text-[11px] font-bold text-slate-600">
                    {finding.title}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-[1.6] text-slate-500">
                    {finding.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Prescription */}
        {entry.prescription && (
          <div className="mx-4 mb-3 rounded-md border border-emerald-200/60 bg-emerald-50/40 px-3 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <Pill className="h-3.5 w-3.5 text-emerald-600" />
                <span className="text-[11px] font-semibold text-emerald-700">
                  Toa thuốc số: {entry.prescription.code} (
                  {entry.prescription.detail})
                </span>
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#0e7490] transition hover:text-[#0c6478]"
              >
                <ExternalLink className="h-2.5 w-2.5" />
                Tải đơn thuốc có chữ ký
              </button>
            </div>
          </div>
        )}

        {/* Prescription note */}
        {entry.prescriptionNote && (
          <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-2.5 text-[11px] text-slate-500">
            <Clock className="h-3 w-3 text-slate-400" />
            {entry.prescriptionNote}
          </div>
        )}

        {/* Summary actions */}
        {entry.summary && (
          <div className="flex flex-wrap items-center gap-2.5 border-t border-slate-100 px-4 py-2.5">
            <button
              type="button"
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0e7490] transition hover:text-[#0c6478]"
            >
              <MessageSquare className="h-3 w-3" />
              Nhắn tin tư vấn với BS. Thảo
            </button>
            <span className="text-slate-200">|</span>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0e7490] transition hover:text-[#0c6478]"
            >
              <CalendarPlus className="h-3 w-3" />
              Đặt lịch khám hô hấp
            </button>
          </div>
        )}

        {/* Test results (health check) */}
        {entry.testResults && entry.testResults.length > 0 && (
          <div className="px-4 py-3">
            <div className="grid gap-2.5 sm:grid-cols-2">
              {entry.testResults.map((test) => (
                <div
                  key={test.id}
                  className="rounded-md border border-slate-200 bg-slate-50/60 p-3"
                >
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-sky-50 text-sky-500">
                      {test.title.includes('X-quang') ? (
                        <Image className="h-4 w-4" />
                      ) : (
                        <BarChart3 className="h-4 w-4" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-bold text-slate-700">
                        {test.title}
                      </p>
                      <p className="mt-0.5 whitespace-pre-line text-[10px] leading-[1.6] text-slate-500">
                        {test.description}
                      </p>
                      {test.hasImageLink && (
                        <button
                          type="button"
                          className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-semibold text-sky-600 transition hover:text-sky-700"
                        >
                          <ExternalLink className="h-2.5 w-2.5" />
                          {test.imageLinkLabel}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Result badge */}
        {entry.resultType && (
          <div className="px-4 pb-2">
            <span className="inline-flex items-center rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200/60">
              {entry.resultType}
            </span>
          </div>
        )}

        {/* Recommendation */}
        {entry.recommendation && (
          <div className="border-t border-slate-100 px-4 py-2.5">
            <p className="text-[11px] italic leading-[1.6] text-slate-500">
              {entry.recommendation}
            </p>
          </div>
        )}

        {/* Additional links */}
        {entry.additionalLinks && entry.additionalLinks.length > 0 && (
          <div className="flex justify-center border-t border-slate-100 py-2.5">
            {entry.additionalLinks.map((link, idx) => (
              <button
                key={idx}
                type="button"
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-500 transition hover:bg-slate-50"
              >
                <Download className="h-3 w-3" />
                {link.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
