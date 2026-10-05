import { Check } from 'lucide-react';
import clsx from 'clsx';
import { Specialty } from '../api';

interface Props {
  specialties: Specialty[];
  selectedId: string;
  onSelect: (id: string) => void;
}

function shortDescription(description: string | null | undefined): string {
  const normalized = description?.replace(/\s+/g, ' ').trim();
  if (!normalized) return 'Chưa có mô tả';

  const firstSentenceEnd = normalized.search(/[.!?](?:\s|$)/);
  const firstSentence = firstSentenceEnd >= 0 ? normalized.slice(0, firstSentenceEnd + 1) : normalized;
  if (firstSentence.length <= 140) return firstSentence;

  const cut = firstSentence.slice(0, 137);
  return `${cut.slice(0, cut.lastIndexOf(' ') > 90 ? cut.lastIndexOf(' ') : cut.length).trimEnd()}…`;
}
export function SpecialtySelector({ specialties, selectedId, onSelect }: Props) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-bold text-slate-900 light:text-app-text">
          <span className="h-2 w-2 rounded-full bg-sky-500 light:bg-app-primary" /> 1. Chuyên khoa
        </h2>
        <span className="text-xs font-medium text-slate-500 light:text-app-secondary">Bắt buộc</span>
      </div>

      {specialties.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 light:border-app-border p-4 text-sm text-slate-500 light:text-app-secondary">
          Chưa có chuyên khoa khả dụng.
        </p>
      ) : (
        <ul className="max-h-80 space-y-1.5 overflow-y-auto pr-1" aria-label="Danh sách chuyên khoa">
          {specialties.map((item) => {
            const isSelected = item.id === selectedId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-pressed={isSelected}
                  title={shortDescription(item.description)}
                  onClick={() => onSelect(item.id)}
                  className={clsx(
                    'flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition-colors',
                    isSelected
                      ? 'border-sky-500 light:border-app-primary bg-sky-50 light:bg-app-muted text-sky-900 light:text-app-primary-strong'
                      : 'border-slate-200 light:border-app-border bg-white light:bg-app-surface text-slate-700 light:text-app-text hover:border-sky-300 hover:bg-sky-50/50 light:hover:bg-app-muted/50',
                  )}
                >
                  <span className="min-w-0 break-words">{item.name}</span>
                  {isSelected && <Check className="h-4 w-4 shrink-0 text-sky-600 light:text-app-primary" aria-hidden="true" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
