import { Check, Clock3, Sparkles, UserRound } from 'lucide-react';
import clsx from 'clsx';
import { Booking } from '../../appointment-booking/api';
import { ProgressStepInfo } from '../types';

interface Props {
  status: Booking['status'];
  progress?: ProgressStepInfo;
  title?: string;
}

const DEFAULT_STEPS = ['Gửi yêu cầu', 'AI phân loại', 'Điều phối xét duyệt', 'Hoàn tất'];

export function HITLProgress({ status, progress, title }: Props) {
  const steps = progress?.steps || DEFAULT_STEPS;
  const currentStep = progress !== undefined ? progress.currentStep : (status === 'pending_approval' ? 2 : status === 'confirmed' ? 3 : 0);
  const stepLabel = progress?.stepLabel || (status === 'pending_approval' ? `Bước ${currentStep + 1}/${steps.length}` : status === 'confirmed' ? 'Hoàn tất' : 'Đã dừng');
  const sectionTitle = title || (progress?.description ? progress.description : 'Tiến trình thực hiện');

  return (
    <div className="rounded-2xl bg-slate-50 dark:bg-app-surface light:bg-app-page p-4 border border-slate-100 dark:border-app-border light:border-app-border">
      <div className="flex items-center justify-between gap-3 text-xs font-bold text-slate-700 dark:text-app-text light:text-app-text">
        <span className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-sky-600 dark:text-sky-400" />
          {sectionTitle}
        </span>
        <span className={clsx(
          'rounded-full px-2 py-0.5 text-[11px] font-bold',
          status === 'pending_approval' ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300' :
          status === 'confirmed' ? 'bg-teal-100 dark:bg-teal-950/60 text-teal-800 dark:text-teal-300' :
          'bg-slate-200 dark:bg-app-muted text-slate-600 dark:text-app-secondary'
        )}>
          {stepLabel}
        </span>
      </div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-app-muted light:bg-app-tint">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-300',
            status === 'confirmed' ? 'w-full bg-teal-600 dark:bg-teal-700' :
            status === 'pending_approval' ? 'bg-amber-500 dark:bg-amber-600' :
            'w-1/4 bg-slate-400'
          )}
          style={{ width: status === 'pending_approval' ? `${Math.min(100, Math.max(25, Math.round(((currentStep + 1) / steps.length) * 100)))}%` : undefined }}
        />
      </div>

      <div className="mt-3 grid grid-cols-4 gap-1">
        {steps.map((step, index) => {
          const done = index < currentStep || (status === 'confirmed' && index <= currentStep);
          const active = index === currentStep && status === 'pending_approval';
          return (
            <div key={step} className="text-center">
              <span className={clsx(
                'mx-auto flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-all',
                done ? 'bg-teal-700 dark:bg-teal-700 text-white shadow-sm' :
                active ? 'bg-amber-500 dark:bg-amber-600 text-white ring-2 ring-amber-300 shadow-sm animate-pulse' :
                'bg-white dark:bg-app-surface light:bg-app-surface text-slate-400 dark:text-app-secondary border border-slate-200 dark:border-app-border',
              )}>
                {done ? <Check className="h-3.5 w-3.5 stroke-[2.5]" /> : active ? <UserRound className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
              </span>
              <span className={clsx(
                'mt-1 block text-[10px] leading-3.5 font-medium',
                active ? 'text-amber-800 dark:text-amber-300 font-bold' :
                done ? 'text-teal-800 dark:text-teal-300' :
                'text-slate-500 dark:text-app-secondary'
              )}>
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

