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
    <div className="ap-steps">
      <div className="ap-steps__head">
        <span><Sparkles size={14} aria-hidden="true" />{sectionTitle}</span>
        <span className="ap-steps__label">{stepLabel}</span>
      </div>
      <ol className="ap-steps__list" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((step, index) => {
          const done = index < currentStep || (status === 'confirmed' && index <= currentStep);
          const active = index === currentStep && status === 'pending_approval';
          return (
            <li key={step} className={clsx('ap-step', done && 'is-done', active && 'is-active')} aria-current={active ? 'step' : undefined}>
              <span className="ap-step__dot">
                {done ? <Check size={14} strokeWidth={3} aria-hidden="true" /> : active ? <UserRound size={14} aria-hidden="true" /> : <Clock3 size={14} aria-hidden="true" />}
              </span>
              {step}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
