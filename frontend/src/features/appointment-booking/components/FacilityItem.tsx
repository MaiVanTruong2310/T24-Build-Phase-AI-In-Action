import React from 'react';
import { MapPin } from 'lucide-react';
import clsx from 'clsx';
import { Facility } from './types';

interface FacilityItemProps {
  facility: Facility;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export const FacilityItem = React.memo(({ facility, isSelected, onSelect }: FacilityItemProps) => {
  return (
    <div 
      onClick={() => onSelect(facility.id)}
      className={clsx(
        "flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition-all duration-200 h-full",
        isSelected 
          ? "border-sky-500 light:border-app-primary bg-sky-50 light:bg-app-muted ring-1 ring-sky-500 light:ring-app-primary" 
          : "border-slate-200 light:border-app-border bg-white light:bg-app-surface hover:border-sky-300 hover:shadow-sm"
      )}
    >
      <div className={clsx(
        "p-2 rounded-lg shrink-0",
        isSelected ? "bg-sky-500 light:bg-app-primary text-white" : "bg-slate-100 light:bg-app-muted text-slate-500 light:text-app-secondary"
      )}>
        <MapPin className="w-5 h-5" />
      </div>
      <div className="flex-1">
        <h4 className="font-bold text-slate-900 light:text-app-text text-sm">{facility.name}</h4>
        <p className="text-xs text-slate-500 light:text-app-secondary mt-1 line-clamp-2">{facility.address}</p>
      </div>
    </div>
  );
});
