import React, { useState, useCallback, useMemo } from 'react';
import { AlertCircle, CheckSquare } from 'lucide-react';
import { SLATimer } from '../features/emergency-coordinator/components/SLATimer';
import { ActionButtons } from '../features/emergency-coordinator/components/ActionButtons';
import { TriageInfo } from '../features/emergency-coordinator/components/TriageInfo';
import { ClinicalChecklist } from '../features/emergency-coordinator/components/ClinicalChecklist';
import { PatientCard } from '../features/emergency-coordinator/components/PatientCard';
import { ChatExtract } from '../features/emergency-coordinator/components/ChatExtract';

const CHECKLIST_TASKS = [
  { id: 'gps', title: 'Đã xác nhận định vị GPS', desc: 'Tòa The Sun, Cầu Giấy' },
  { id: 'an', title: 'Đã đàm thoại trấn an BN', desc: 'Hướng dẫn nằm nghỉ ngơi' },
  { id: '115', title: 'Đã điều xe Cấp cứu 115', desc: 'Mã kíp trực: 115-HN-04' },
  { id: 'cath', title: 'Kích hoạt Cathlab Can thiệp', desc: 'Phòng DSA số 2 - BV MediCare' },
];

export default function EmergencyCoordinator() {
  // Page logic: Patient data
  const patientData = useMemo(() => ({
    name: "Vũ Thành Long",
    age: "46 tuổi • Nam",
    id: "BN-89240",
    phone: "0912 345 678",
    kin: "Lê Thị Mai (Vợ) - 0987 654 321",
    history: ["Tăng huyết áp vô căn (4 năm)", "Rối loạn lipid máu", "Dị ứng: Penicillin G"]
  }), []);

  // Page logic: Checklist state
  const [checkedTasks, setCheckedTasks] = useState<Record<string, boolean>>({});
  
  const handleToggleTask = useCallback((id: string) => {
    setCheckedTasks(prev => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Page logic: Clinical Notes
  const [notes, setNotes] = useState('');

  const handleSaveDraft = () => {
    console.log("Saving draft:", { checkedTasks, notes });
  };

  const handleComplete = () => {
    console.log("Completing protocol:", { checkedTasks, notes });
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      {/* Header */}
      <header className="bg-red-700 text-white p-4 sticky top-0 z-10 shadow-md">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center animate-pulse">
              <AlertCircle className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold uppercase tracking-wider flex items-center gap-2">
                Ca Cấp Cứu Lâm Sàng Đang Xử Lý 
                <span className="bg-white text-red-700 text-xs px-2 py-1 rounded-full font-bold">ESC-0911-CRITICAL</span>
              </h1>
              <p className="opacity-90 flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-red-400 animate-ping"></span>
                ĐANG ĐIỀU PHỐI KHẨN CẤP | Kích hoạt: 04 phút trước (14:32:10)
              </p>
            </div>
          </div>
          <SLATimer />
        </div>
      </header>

      <main className="max-w-7xl mx-auto mt-6 px-4 space-y-6">
        <ActionButtons />

        <div className="grid grid-cols-3 gap-6">
          {/* Left Column (Clinical) */}
          <div className="col-span-2 space-y-6">
            <TriageInfo />
            <ChatExtract />
          </div>

          {/* Right Column (Patient & Protocol) */}
          <div className="space-y-6">
            <PatientCard data={patientData} />

            {/* Protocol Card - Page handles the logic, composed here */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <CheckSquare className="w-5 h-5 text-teal-600" />
                  Biên Bản & Quy Trình
                </h3>
                <span className="bg-teal-100 text-teal-800 text-xs px-2 py-1 rounded font-semibold">HITL ACTIVE NOTE</span>
              </div>
              
              <ClinicalChecklist 
                tasks={CHECKLIST_TASKS}
                checked={checkedTasks}
                onToggle={handleToggleTask}
              />
              
              <div className="mt-4">
                <label className="block text-sm font-semibold text-gray-700 mb-2">Nhật ký y lệnh điều phối viên</label>
                <textarea 
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  rows={3}
                  placeholder="Nhập ghi chú xử lý ca..."
                />
              </div>
              
              <div className="mt-6 flex gap-3">
                <button 
                  onClick={handleSaveDraft}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-lg font-semibold transition-colors"
                >
                  Lưu nháp
                </button>
                <button 
                  onClick={handleComplete}
                  className="flex-1 bg-teal-700 hover:bg-teal-800 text-white py-3 rounded-lg font-semibold transition-colors shadow-sm"
                >
                  Hoàn tất điều phối
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
