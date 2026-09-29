import { useState } from 'react';
import { Search, Activity, Gauge, Pill, UserCheck } from 'lucide-react';
import { PatientQueueItem, PatientStatus, HITLMetrics } from '../types';

interface QueueSidebarProps {
  patients: PatientQueueItem[];
  selectedPatientId: string;
  onSelectPatient: (patientId: string) => void;
  metrics: HITLMetrics;
}

export function QueueSidebar({
  patients,
  selectedPatientId,
  onSelectPatient,
  metrics,
}: QueueSidebarProps) {
  const [activeTab, setActiveTab] = useState<PatientStatus>('need_takeover');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPatients = patients.filter((patient) => {
    const matchesTab = activeTab === 'need_takeover' ? true : patient.status === activeTab;
    const matchesSearch =
      patient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      patient.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      patient.lastSnippet.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <aside className="w-80 xl:w-88 shrink-0 flex flex-col bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden h-[calc(100vh-140px)] min-h-[640px]">
      {/* Header */}
      <div className="p-4 border-b border-slate-100">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
              <Activity size={16} />
            </div>
            <h2 className="text-base font-bold text-slate-800">Hàng đợi Giám sát</h2>
          </div>
          <span className="px-2.5 py-0.5 text-xs font-bold text-slate-600 bg-slate-100 rounded-full border border-slate-200">
            Tổng {metrics.totalQueue} ca
          </span>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên bệnh nhân, mã hồ sơ hoặc triệu ch..."
            className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-sky-500 focus:ring-1 focus:ring-sky-500 outline-none transition-all placeholder:text-slate-400 text-slate-700"
          />
        </div>

        {/* Tab Filters */}
        <div className="grid grid-cols-3 gap-1 mt-3 bg-slate-100 p-1 rounded-xl text-center">
          <button
            onClick={() => setActiveTab('need_takeover')}
            className={`py-1.5 px-1 text-[11px] font-bold rounded-lg transition-all ${
              activeTab === 'need_takeover'
                ? 'bg-white text-rose-600 shadow-2xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Cần tiếp quản{' '}
            <span className="ml-0.5 px-1 py-0.2 rounded-full text-[10px] bg-rose-100 text-rose-700">
              {metrics.needTakeoverCount}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('in_intervention')}
            className={`py-1.5 px-1 text-[11px] font-bold rounded-lg transition-all ${
              activeTab === 'in_intervention'
                ? 'bg-white text-sky-700 shadow-2xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Đang can thiệp{' '}
            <span className="ml-0.5 px-1 py-0.2 rounded-full text-[10px] bg-sky-100 text-sky-700">
              {metrics.inInterventionCount}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('ai_handling')}
            className={`py-1.5 px-1 text-[11px] font-bold rounded-lg transition-all ${
              activeTab === 'ai_handling'
                ? 'bg-white text-emerald-700 shadow-2xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            AI tự xử lý{' '}
            <span className="ml-0.5 px-1 py-0.2 rounded-full text-[10px] bg-emerald-100 text-emerald-700">
              {metrics.aiHandlingCount}
            </span>
          </button>
        </div>
      </div>

      {/* Patient List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1">
        {filteredPatients.map((patient) => {
          const isSelected = patient.id === selectedPatientId;
          const isCritical = patient.priority === 'critical';

          return (
            <div
              key={patient.id}
              onClick={() => onSelectPatient(patient.id)}
              className={`p-3 rounded-xl cursor-pointer transition-all border text-left ${
                isSelected
                  ? 'bg-rose-50/60 border-rose-200 shadow-2xs ring-1 ring-rose-300'
                  : 'bg-white border-transparent hover:bg-slate-50 hover:border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2.5">
                  <div className="relative shrink-0">
                    {patient.avatar ? (
                      <img
                        src={patient.avatar}
                        alt={patient.name}
                        className="w-9 h-9 rounded-full object-cover border border-slate-200 shadow-2xs"
                      />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-teal-100 text-teal-800 font-bold text-xs flex items-center justify-center border border-teal-200">
                        {patient.name.split(' ').slice(-2).map((n) => n[0]).join('')}
                      </div>
                    )}
                    {isCritical && (
                      <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-rose-600 text-white rounded-full flex items-center justify-center text-[9px] font-black border-2 border-white">
                        !
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 leading-tight">
                      {patient.name}
                      <span className="text-[11px] font-normal text-slate-500">
                        {patient.age} tuổi • {patient.gender}
                      </span>
                    </h3>
                    <p className="text-[10px] text-slate-500 font-medium">{patient.code}</p>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${
                    isCritical
                      ? 'bg-rose-600 text-white'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {patient.timeAgo}
                </span>
              </div>

              {/* Special category tag if present */}
              {patient.categoryTag && (
                <div className="mb-1.5">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-100 leading-tight">
                    {patient.categoryTag.includes('THUỐC') ? (
                      <Pill size={11} className="text-sky-600 shrink-0" />
                    ) : (
                      <UserCheck size={11} className="text-sky-600 shrink-0" />
                    )}
                    <span className="truncate max-w-[210px]">{patient.categoryTag}</span>
                  </span>
                </div>
              )}

              {/* Message Snippet */}
              <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed mb-2 font-normal italic">
                "{patient.lastSnippet}"
              </p>

              {/* Card Footer tags */}
              {patient.subStatus && (
                <div className="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-100 pt-1.5 font-medium">
                  <span className="text-sky-700 font-semibold">{patient.subStatus}</span>
                  {patient.confidence !== undefined && (
                    <span className="text-slate-600">
                      Độ tin cậy AI: <strong>{patient.confidence}%</strong>
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Performance Card */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/80">
        <div className="bg-white rounded-xl p-3 border border-slate-200 shadow-2xs flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <Gauge size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800 leading-tight">Hiệu suất HITL Ca trực</p>
              <p className="text-[10px] text-slate-500 leading-tight mt-0.5">
                {metrics.completedCasesCount} ca xử lý xong • {metrics.zeroDefectCount} sai lệch lâm sàng
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-base font-black text-emerald-600 leading-none">{metrics.shiftAccuracyPercent}%</p>
            <p className="text-[10px] text-slate-400 font-medium leading-tight mt-0.5">An toàn chuẩn</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
