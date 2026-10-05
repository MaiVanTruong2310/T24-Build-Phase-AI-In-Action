import React, { memo } from 'react';
import { CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import { Specialty } from './types';

type Props = {
  item: Specialty;
  isSelected: boolean;
  onSelect: (id: string) => void;
};

export const SpecialtyItem = memo(({ item, isSelected, onSelect }: Props) => {
  const Icon = item.icon;
  return (
    <button
      onClick={() => onSelect(item.id)}
      className={clsx(
        "w-full text-left p-4 rounded-xl border flex items-center justify-between transition-all duration-200 h-full",
        isSelected ? "border-sky-500 light:border-app-primary bg-sky-50 light:bg-app-muted ring-1 ring-sky-500 light:ring-app-primary" : "border-slate-200 light:border-app-border bg-white light:bg-app-surface hover:border-sky-300 hover:shadow-sm"
      )}
    >
      <div className="flex items-center gap-4">
        <div className={clsx("p-3 rounded-lg shrink-0 transition-colors", isSelected ? "bg-sky-500 light:bg-app-primary text-white" : "bg-slate-100 light:bg-app-muted text-slate-500 light:text-app-secondary")}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h4 className={clsx("font-semibold text-base transition-colors", isSelected ? "text-sky-900 light:text-app-primary-strong" : "text-slate-800 light:text-app-text")}>{item.name}</h4>
          <p className={clsx("text-xs mt-0.5 line-clamp-1 transition-colors", isSelected ? "text-sky-700 light:text-app-primary" : "text-slate-500 light:text-app-secondary")}>{item.desc}</p>
        </div>
      </div>
      {isSelected && <CheckCircle2 className="w-5 h-5 text-sky-500 light:text-app-primary shrink-0 ml-2" />}
    </button>
  );
});
