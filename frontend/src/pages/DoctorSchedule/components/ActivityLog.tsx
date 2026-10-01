import { Activity, CheckCircle2, Clock3, FilePlus2, RotateCcw, XCircle } from 'lucide-react';
import { Doctor, Schedule, ScheduleAuditEvent } from '../../../features/appointment-booking/api';

interface ActivityLogProps {
  doctor: Doctor | null;
  schedules: Schedule[];
  events: ScheduleAuditEvent[];
  loading?: boolean;
  error?: string;
}

const actionMeta: Record<string, { label: string; icon: typeof Activity; className: string }> = {
  created: { label: 'Đã tạo', icon: FilePlus2, className: 'bg-sky-50 text-sky-600' },
  updated: { label: 'Đã cập nhật', icon: RotateCcw, className: 'bg-amber-50 text-amber-600' },
  cancelled: { label: 'Đã hủy', icon: XCircle, className: 'bg-rose-50 text-rose-600' },
  imported: { label: 'Đã đồng bộ', icon: CheckCircle2, className: 'bg-emerald-50 text-emerald-600' },
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function timeRange(schedule?: Schedule): string {
  if (!schedule) return 'Lịch không còn trong danh sách hiện tại';
  const start = new Date(schedule.starts_at).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  const end = new Date(schedule.ends_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  return `${start} - ${end}`;
}

function locationLabel(doctor: Doctor | null, schedule?: Schedule): string {
  if (!doctor || !schedule) return 'Chưa xác định địa điểm';
  if (!schedule.facility_id) return 'Tất cả cơ sở';
  const assignment = doctor.facilities?.find((item) => item.facility_id === schedule.facility_id);
  const facility = assignment?.facility?.name || `Cơ sở ${schedule.facility_id.slice(0, 8)}`;
  return assignment?.room ? `${facility} • Phòng ${assignment.room}` : facility;
}

function actorLabel(actorId: string | null): string {
  return actorId ? `Người thực hiện: ${actorId.slice(0, 8)}` : 'Hệ thống tự động';
}

function actionText(event: ScheduleAuditEvent, schedule?: Schedule): string {
  const range = timeRange(schedule);
  if (event.action === 'created') return `Tạo lịch khám ${range}`;
  if (event.action === 'updated') return `Cập nhật lịch khám ${range}`;
  if (event.action === 'cancelled') return `Hủy lịch khám ${range}`;
  if (event.action === 'imported') return `Đồng bộ lịch khám ${range}`;
  return `Thao tác ${event.action} trên lịch ${range}`;
}

export function ActivityLog({ doctor, schedules, events, loading = false, error = '' }: ActivityLogProps) {
  const scheduleById = new Map(schedules.map((schedule) => [schedule.id, schedule]));

  return (
    <div className="relative rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800"><Clock3 size={20} className="text-sky-600" /> Nhật ký thao tác & điều phối lịch ca trực</h3>
        <span className="text-xs font-medium text-slate-500">Dữ liệu audit thực tế</span>
      </div>

      {loading && <div className="rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-500">Đang tải nhật ký thao tác...</div>}
      {error && !loading && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{error}</div>}
      {!loading && !error && events.length === 0 && <div className="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">Chưa có thao tác nào trong khoảng thời gian đang xem.</div>}

      {!loading && !error && events.length > 0 && (
        <div className="relative space-y-6 before:absolute before:inset-y-0 before:left-[19px] before:w-0.5 before:bg-slate-100">
          {events.map((event) => {
            const meta = actionMeta[event.action] || { label: event.action, icon: Activity, className: 'bg-slate-50 text-slate-600' };
            const Icon = meta.icon;
            const schedule = scheduleById.get(event.entity_id);
            return (
              <div key={event.id} className="relative flex gap-4">
                <div className={`z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-white shadow-sm ${meta.className}`}><Icon size={16} /></div>
                <div className="min-w-0 flex-1 pt-1">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm leading-relaxed text-slate-700"><span className="font-bold text-slate-900">{actionText(event, schedule)}</span><span className="ml-2 text-slate-500">• {locationLabel(doctor, schedule)}</span></p>
                    <span className={`shrink-0 rounded px-2 py-1 text-[10px] font-bold ${meta.className}`}>{meta.label}</span>
                  </div>
                  <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400"><span>{formatDateTime(event.created_at)}</span><span>•</span><span>{actorLabel(event.actor_id)}</span>{typeof event.payload.version === 'number' && <><span>•</span><span>Phiên bản v{event.payload.version}</span></>}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
