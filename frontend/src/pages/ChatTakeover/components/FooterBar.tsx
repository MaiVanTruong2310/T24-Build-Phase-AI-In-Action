import { ShieldCheck } from 'lucide-react';

interface FooterBarProps {
  auditId?: string;
  roomName?: string;
}

export function FooterBar({
  auditId = 'MC-HITL-2024-SYS',
  roomName = 'Phòng Trực Cấp Cứu 01',
}: FooterBarProps) {
  return (
    <footer className="mt-4 pt-3 pb-2 border-t border-slate-200/80 text-[11px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2 px-1">
      <div className="flex items-center gap-2">
        <ShieldCheck size={15} className="text-teal-600 shrink-0" />
        <span>
          VCare+ Clinical HITL Management System - Chuẩn HIPAA & Bộ Y Tế. Hệ thống tự động ghi nhật ký can thiệp y khoa.
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0 font-medium">
        <span>
          Audit ID: <strong className="text-slate-700">{auditId}</strong>
        </span>
        <span className="text-slate-300">•</span>
        <span>
          Phiên trực: <strong className="text-slate-700">{roomName}</strong>
        </span>
      </div>
    </footer>
  );
}
