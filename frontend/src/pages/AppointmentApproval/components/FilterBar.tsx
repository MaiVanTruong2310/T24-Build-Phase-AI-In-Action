import { Search, ArrowUpDown } from 'lucide-react';
import type { TabFilter, BookingCounts } from './constants';

interface FilterBarProps {
  activeTab: TabFilter;
  onTabChange: (tab: TabFilter) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  sortBy: 'time' | 'risk';
  onSortToggle: () => void;
  counts: BookingCounts;
}

export function FilterBar({
  activeTab,
  onTabChange,
  searchQuery,
  onSearchChange,
  sortBy,
  onSortToggle,
  counts,
}: FilterBarProps) {
  const tabs: { key: TabFilter; label: string; count: number }[] = [
    { key: 'all', label: 'Tất cả', count: counts.all },
    { key: 'pending_approval', label: 'Chờ duyệt', count: counts.pending_approval },
    { key: 'confirmed', label: 'Đã duyệt', count: counts.confirmed },
    { key: 'rejected', label: 'Đã từ chối', count: counts.rejected },
  ];

  return (
    <div className="bg-white border-b border-slate-100 px-6 py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 flex-shrink-0">
      {/* Tabs */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              activeTab === tab.key
                ? 'bg-white text-sky-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
            <span
              className={`ml-1.5 px-1.5 py-0.5 text-[10px] rounded-full font-bold ${
                activeTab === tab.key
                  ? 'bg-sky-100 text-sky-700'
                  : 'bg-slate-200 text-slate-500'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Search + Sort */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Tìm bệnh nhân, bác sĩ, mã hẹn..."
            className="w-64 pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-sky-400 focus:ring-2 focus:ring-sky-100 transition-all outline-none"
          />
        </div>
        <button
          onClick={onSortToggle}
          className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <ArrowUpDown size={14} />
          {sortBy === 'time' ? 'Theo giờ khám' : 'Theo mức rủi ro'}
        </button>
      </div>
    </div>
  );
}
