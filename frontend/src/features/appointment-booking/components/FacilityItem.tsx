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
          ? "border-sky-500 bg-sky-50 ring-1 ring-sky-500" 
          : "border-slate-200 bg-white hover:border-sky-300 hover:shadow-sm"
      )}
    >
      <div className={clsx(
        "p-2 rounded-lg shrink-0",
        isSelected ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-500"
      )}>
        <MapPin className="w-5 h-5" />
      </div>
      <div className="flex-1">
        <h4 className="font-bold text-slate-900 text-sm">{facility.name}</h4>
        <p className="text-xs text-slate-500 mt-1 line-clamp-2">{facility.address}</p>
      </div>
    </div>
  );
});
