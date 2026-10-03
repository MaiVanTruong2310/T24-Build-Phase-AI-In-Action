import { BellRing, X } from 'lucide-react';

interface Props {
  message: string | null;
  onDismiss: () => void;
}

export function CoordinatorNotice({ message, onDismiss }: Props) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-teal-100 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/50 p-4 text-teal-900 dark:text-teal-300 shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-700 dark:bg-teal-700 text-white"><BellRing className="h-5 w-5" /></div>
      <div className="min-w-0 flex-1"><p className="text-xs font-bold uppercase tracking-wide text-teal-700 dark:text-teal-300">Thông báo điều phối viên</p><p className="mt-1 text-sm font-semibold leading-6">{message}</p></div>
      <button type="button" onClick={onDismiss} aria-label="Đóng thông báo" className="rounded-lg p-1 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-950/50"><X className="h-5 w-5" /></button>
    </div>
  );
}
