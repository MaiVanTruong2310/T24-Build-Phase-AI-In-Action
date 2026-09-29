import { CheckCircle2, ChevronRight, HeartPulse } from 'lucide-react';
import clsx from 'clsx';
import { Specialty } from '../api';

interface Props {
  specialties: Specialty[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function SpecialtySelector({ specialties, selectedId, onSelect }: Props) {
  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-bold text-slate-900">
          <span className="h-2 w-2 rounded-full bg-sky-500" /> 1. Chuyên khoa
        </h2>
        <span className="text-xs font-medium text-slate-500">Bắt buộc</span>
      </div>

      <div className="space-y-2">
        {specialties.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            Chưa có chuyên khoa khả dụng.
          </p>
        )}
        {specialties.map((item) => {
          const isSelected = item.id === selectedId;
          return (
            <button
              type="button"
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={clsx(
                'group flex w-full items-center justify-between rounded-xl border p-3 text-left transition-all',
                isSelected
                  ? 'border-sky-500 bg-sky-50 shadow-sm ring-1 ring-sky-500'
                  : 'border-slate-200 bg-white hover:border-sky-300',
              )}
            >
              <span className="flex items-center gap-3">
                <span className={clsx('shrink-0 rounded-lg p-2.5', isSelected ? 'bg-sky-600 text-white' : 'bg-slate-100 text-slate-500')}>
                  <HeartPulse className="h-5 w-5" />
                </span>
                <span>
                  <span className={clsx('block text-sm font-semibold', isSelected ? 'text-sky-900' : 'text-slate-800')}>
                    {item.name}
                  </span>
                  <span className="mt-0.5 block text-xs text-slate-500">{item.description || 'Chưa có mô tả'}</span>
                </span>
              </span>
              {isSelected ? <CheckCircle2 className="h-5 w-5 shrink-0 text-sky-600" /> : <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />}
            </button>
          );
        })}
      </div>
    </section>
  );
}
