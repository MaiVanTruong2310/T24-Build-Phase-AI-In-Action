import React, { memo } from 'react';
import clsx from 'clsx';
import { TimeSlot } from './types';

type Props = {
  slot: TimeSlot;
  isSelected: boolean;
  onSelect: (id: string) => void;
};

export const SlotItem = memo(({ slot, isSelected, onSelect }: Props) => {
  const disabled = slot.status === 'booked';
  return (
    <button
      disabled={disabled}
      onClick={() => onSelect(slot.id)}
      className={clsx(
        "p-3 rounded-lg border text-center transition-all relative overflow-hidden",
        disabled && "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed opacity-60",
        isSelected && "bg-sky-600 light:bg-app-primary border-sky-600 light:border-app-primary text-white shadow-md transform scale-[1.02]",
        !disabled && !isSelected && "bg-white light:bg-app-surface border-slate-200 light:border-app-border text-slate-700 light:text-app-text hover:border-sky-500 light:hover:border-app-primary hover:shadow-sm"
      )}
    >
      {isSelected && <div className="absolute top-0 right-0 w-4 h-4 bg-sky-400 light:bg-app-primary rounded-bl-lg" />}
      <div className="font-bold text-lg">{slot.time}</div>
      <div className="text-xs mt-1">
        {disabled ? 'Đã kín lịch' : isSelected ? 'Đang chọn' : 'Trống chỗ'}
      </div>
    </button>
  );
});
