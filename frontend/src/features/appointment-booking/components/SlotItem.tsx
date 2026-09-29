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
        isSelected && "bg-sky-600 border-sky-600 text-white shadow-md transform scale-[1.02]",
        !disabled && !isSelected && "bg-white border-slate-200 text-slate-700 hover:border-sky-500 hover:shadow-sm"
      )}
    >
      {isSelected && <div className="absolute top-0 right-0 w-4 h-4 bg-sky-400 rounded-bl-lg" />}
      <div className="font-bold text-lg">{slot.time}</div>
      <div className="text-xs mt-1">
        {disabled ? 'Đã kín lịch' : isSelected ? 'Đang chọn' : 'Trống chỗ'}
      </div>
    </button>
  );
});
