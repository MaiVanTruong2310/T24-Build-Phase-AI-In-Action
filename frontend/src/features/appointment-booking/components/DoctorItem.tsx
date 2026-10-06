import React from 'react';
import { Star } from 'lucide-react';
import clsx from 'clsx';
import { Doctor } from './types';

interface DoctorItemProps {
  doctor: Doctor;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export const DoctorItem = React.memo(({ doctor, isSelected, onSelect }: DoctorItemProps) => {
  return (
    <div 
      onClick={() => onSelect(doctor.id)}
      className={clsx(
        "flex items-center gap-4 p-4 rounded-xl border cursor-pointer transition-all duration-200",
        isSelected 
          ? "border-sky-500 light:border-app-primary bg-sky-50 light:bg-app-muted ring-1 ring-sky-500 light:ring-app-primary" 
          : "border-slate-200 light:border-app-border bg-white light:bg-app-surface hover:border-sky-300 hover:shadow-sm"
      )}
    >
      <img 
        src={doctor.avatar} 
        alt={doctor.name} 
        className="w-16 h-16 rounded-full object-cover border border-slate-200 light:border-app-border"
      />
      <div className="flex-1">
        <h4 className="font-bold text-slate-900 light:text-app-text">{doctor.title} {doctor.name}</h4>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex items-center text-amber-500 text-xs font-semibold">
            <Star className="w-3.5 h-3.5 fill-current mr-0.5" />
            {doctor.rating.toFixed(1)}
          </div>
          <span className="text-slate-300 text-xs">•</span>
          <span className="text-xs text-slate-500 light:text-app-secondary">Chuyên gia Y tế</span>
        </div>
      </div>
      <div className="shrink-0 flex items-center justify-center">
        <div className={clsx(
          "w-5 h-5 rounded-full border flex items-center justify-center transition-colors",
          isSelected ? "border-sky-500 light:border-app-primary bg-sky-500 light:bg-app-primary" : "border-slate-300 light:border-app-border"
        )}>
          {isSelected && <div className="w-2 h-2 bg-white light:bg-app-surface rounded-full" />}
        </div>
      </div>
    </div>
  );
});
