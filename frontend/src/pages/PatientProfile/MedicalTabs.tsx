import { memo } from 'react';
import type { MedicalTab as MedicalTabType } from './types';

interface MedicalTabsProps {
  tabs: MedicalTabType[];
  activeTab: string;
  onTabChange: (key: string) => void;
}

export const MedicalTabs = memo(function MedicalTabs({
  tabs,
  activeTab,
  onTabChange,
}: MedicalTabsProps) {
  return (
    <div className="flex flex-wrap items-center gap-0 rounded-xl border border-slate-200 light:border-app-border bg-white light:bg-app-surface shadow-sm">
      {tabs.map((tab) => {
        const isActive = tab.key === activeTab;
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onTabChange(tab.key)}
            className={`relative px-5 py-3 text-[13px] font-medium transition first:rounded-l-xl last:rounded-r-xl ${
              isActive
                ? 'bg-[#0e7490] light:bg-app-primary text-white font-semibold'
                : 'text-slate-500 light:text-app-secondary hover:bg-slate-50 light:hover:bg-app-page hover:text-slate-700 light:hover:text-app-text'
            }`}
          >
            {tab.label}
            {tab.count != null && (
              <span
                className={`ml-1 text-[12px] ${
                  isActive ? 'text-white/70' : 'text-slate-400 light:text-app-secondary'
                }`}
              >
                ({tab.count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
});
