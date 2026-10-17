import { memo, useState } from 'react';
import { Check, ChevronDown, Pencil } from 'lucide-react';
import type { ConsultationProgressData, ProgressStepKey } from './api';
import { SosButton } from './SosButton';
import './ConsultationProgress.css';

interface ConsultationProgressProps {
  progress: ConsultationProgressData;
  onEdit: (step: ProgressStepKey) => void;
  disabled?: boolean;
}

// Các bước người bệnh có thể sửa lại bằng lời (đặt lịch sửa trong Phiếu khám).
const EDITABLE: ProgressStepKey[] = ['symptom', 'details'];

export const ConsultationProgress = memo(function ConsultationProgress({ progress, onEdit, disabled = false }: ConsultationProgressProps) {
  const [expanded, setExpanded] = useState(false);
  if (progress.emergency) {
    return (
      <div className="consult-progress consult-progress--emergency" role="status">
        <strong>Có dấu hiệu cần cấp cứu.</strong> Hãy gọi <SosButton variant="link" /> hoặc đến cơ sở cấp cứu gần nhất ngay.
      </div>
    );
  }
  const current = progress.steps[progress.current_step - 1] ?? progress.steps[progress.steps.length - 1];

  return (
    <nav className={`consult-progress ${expanded ? 'is-expanded' : ''}`} aria-label="Tiến trình tư vấn">
      <button type="button" className="consult-progress__toggle" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
        <span>Bước {progress.current_step}/{progress.steps.length} · {current.label}</span>
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
      </button>
      <ol className="consult-progress__steps">
        {progress.steps.map((step, index) => (
          <li key={step.key} className={`consult-progress__step is-${step.status}`} aria-current={step.status === 'current' ? 'step' : undefined}>
            <span className="consult-progress__dot" aria-hidden="true">
              {step.status === 'done' ? <Check className="h-3.5 w-3.5" /> : index + 1}
            </span>
            <span className="consult-progress__body">
              <span className="consult-progress__label">
                {step.label}
                {step.status === 'skipped' && <span className="consult-progress__muted"> · bỏ qua</span>}
              </span>
              {step.summary && <span className="consult-progress__summary" title={step.summary}>{step.summary}</span>}
            </span>
            {step.summary && step.status !== 'skipped' && EDITABLE.includes(step.key) && (
              <button type="button" disabled={disabled} className="consult-progress__edit" onClick={() => onEdit(step.key)}
                aria-label={`Sửa: ${step.label}`} title="Em hiểu chưa đúng? Bấm để sửa">
                <Pencil className="h-3 w-3" aria-hidden="true" /><span className="consult-progress__edit-label">Sửa</span>
              </button>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
});
