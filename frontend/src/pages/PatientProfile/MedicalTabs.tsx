import { memo } from 'react';
import type { MedicalTab as MedicalTabType } from './types';

interface MedicalTabsProps {
  tabs: MedicalTabType[];
  activeTab: string;
  onTabChange: (key: string) => void;
}

export const MedicalTabs = memo(function MedicalTabs({ tabs, activeTab, onTabChange }: MedicalTabsProps) {
  return (
    <div className="pp-tabs" role="group" aria-label="Loại hồ sơ khám">
      {tabs.map((tab) => (
        <button key={tab.key} type="button" aria-pressed={tab.key === activeTab} onClick={() => onTabChange(tab.key)} className="pp-chip">
          {tab.label}
          {tab.count != null && <span className="pp-chip__n">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
});
