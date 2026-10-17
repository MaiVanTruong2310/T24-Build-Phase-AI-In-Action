import { History, ArrowRight } from 'lucide-react';
import { AuditLogItem } from '../types';

interface AuditLogCardProps {
  logs: AuditLogItem[];
  onViewAllLogs?: () => void;
}

export function AuditLogCard({ logs, onViewAllLogs }: AuditLogCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-2xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-sky-50 text-sky-600 flex items-center justify-center">
            <History size={15} />
          </div>
          <h3 className="text-sm font-extrabold text-slate-800">Nhật ký can thiệp (Audit)</h3>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          Live sync
        </span>
      </div>

      {/* Log entries */}
      <div className="space-y-3">
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2.5 text-xs">
            <span
              className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                log.isCritical ? 'bg-rose-600' : 'bg-slate-300'
              }`}
            />
            <div className="min-w-0 flex-1 leading-relaxed">
              <span className="font-bold text-slate-700">{log.time}</span>
              <span className="text-slate-400 mx-1">•</span>
              <span className="font-extrabold text-slate-900">{log.actor}</span>
              <p className="text-slate-600 font-medium text-[11px] mt-0.5">
                {log.action}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Link */}
      <div className="pt-2 border-t border-slate-100">
        <button
          type="button"
          onClick={onViewAllLogs}
          className="text-xs font-bold text-sky-700 hover:text-sky-800 flex items-center gap-1 transition-colors"
        >
          <span>Xem toàn bộ sổ nhật ký điện tử (HIPAA Compliant)</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}
