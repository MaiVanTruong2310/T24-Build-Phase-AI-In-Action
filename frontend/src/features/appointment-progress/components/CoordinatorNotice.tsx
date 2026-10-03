import { BellRing, X } from 'lucide-react';

interface Props {
  message: string | null;
  onDismiss: () => void;
}

export function CoordinatorNotice({ message, onDismiss }: Props) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-teal-100 bg-teal-50 p-4 text-teal-900 shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-700 text-white"><BellRing className="h-5 w-5" /></div>
      <div className="min-w-0 flex-1"><p className="text-xs font-bold uppercase tracking-wide text-teal-700">Thông báo điều phối viên</p><p className="mt-1 text-sm font-semibold leading-6">{message}</p></div>
      <button type="button" onClick={onDismiss} aria-label="Đóng thông báo" className="rounded-lg p-1 text-teal-700 hover:bg-teal-100"><X className="h-5 w-5" /></button>
    </div>
  );
}
