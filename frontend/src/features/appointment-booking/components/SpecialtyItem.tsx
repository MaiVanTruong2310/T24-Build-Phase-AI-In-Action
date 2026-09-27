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
        isSelected ? "border-sky-500 bg-sky-50 ring-1 ring-sky-500" : "border-slate-200 bg-white hover:border-sky-300 hover:shadow-sm"
      )}
    >
      <div className="flex items-center gap-4">
        <div className={clsx("p-3 rounded-lg shrink-0 transition-colors", isSelected ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-500")}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h4 className={clsx("font-semibold text-base transition-colors", isSelected ? "text-sky-900" : "text-slate-800")}>{item.name}</h4>
          <p className={clsx("text-xs mt-0.5 line-clamp-1 transition-colors", isSelected ? "text-sky-700" : "text-slate-500")}>{item.desc}</p>
        </div>
      </div>
      {isSelected && <CheckCircle2 className="w-5 h-5 text-sky-500 shrink-0 ml-2" />}
    </button>
  );
});
