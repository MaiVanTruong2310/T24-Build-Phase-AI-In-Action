import { Check, Clock3, UserRound } from 'lucide-react';
import clsx from 'clsx';
import { Booking } from '../../appointment-booking/api';

interface Props {
  status: Booking['status'];
}

const steps = ['Gửi yêu cầu', 'AI phân loại', 'Điều phối xét duyệt', 'Hoàn tất'];

export function HITLProgress({ status }: Props) {
  const currentStep = status === 'pending_approval' ? 2 : status === 'confirmed' ? 3 : 0;
  return (
    <div className="rounded-2xl bg-slate-50 dark:bg-app-surface light:bg-app-page p-4">
      <div className="flex items-center justify-between gap-3 text-xs font-bold text-slate-600 dark:text-app-secondary light:text-app-secondary">
        <span>Tiến trình xét duyệt HITL</span>
        <span className={status === 'pending_approval' ? 'text-amber-700 dark:text-amber-300' : status === 'confirmed' ? 'text-teal-700 dark:text-teal-300' : 'text-slate-500 dark:text-app-secondary light:text-app-secondary'}>
          {status === 'pending_approval' ? 'Bước 3/4' : status === 'confirmed' ? 'Hoàn tất' : 'Đã dừng'}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-app-muted light:bg-app-tint">
        <div className={clsx('h-full rounded-full transition-all', status === 'confirmed' ? 'w-full bg-teal-600 dark:bg-teal-700' : status === 'pending_approval' ? 'w-3/4 bg-amber-500 dark:bg-amber-700' : 'w-1/4 bg-slate-400')} />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-1">
        {steps.map((step, index) => {
          const done = index < currentStep;
          const active = index === currentStep && status === 'pending_approval';
          return (
            <div key={step} className="text-center">
              <span className={clsx(
                'mx-auto flex h-7 w-7 items-center justify-center rounded-full text-xs',
                done ? 'bg-teal-700 dark:bg-teal-700 text-white' : active ? 'bg-amber-500 dark:bg-amber-700 text-white' : 'bg-white dark:bg-app-surface light:bg-app-surface text-slate-400 dark:text-app-secondary light:text-app-secondary',
              )}>
                {done ? <Check className="h-3.5 w-3.5" /> : active ? <UserRound className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
              </span>
              <span className="mt-1 block text-[10px] leading-4 text-slate-500 dark:text-app-secondary light:text-app-secondary">{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
