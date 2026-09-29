import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MOCK_PATIENTS, INITIAL_METRICS } from './mockData';
import { PatientQueueItem, ChatMessage } from './types';
import { TopAlertBanner } from './components/TopAlertBanner';
import { QueueSidebar } from './components/QueueSidebar';
import { PatientHeader } from './components/PatientHeader';
import { MessageList } from './components/MessageList';
import { ChatInputArea } from './components/ChatInputArea';
import { VitalsCard } from './components/VitalsCard';
import { AITriageCard } from './components/AITriageCard';
import { ProtocolCard } from './components/ProtocolCard';
import { FooterBar } from './components/FooterBar';

export default function ChatTakeover() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientQueueItem[]>(MOCK_PATIENTS);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('p-8831');
  const [isTakenOver, setIsTakenOver] = useState<boolean>(false);
  const [isSigned, setIsSigned] = useState<boolean>(false);
  const [metrics] = useState(INITIAL_METRICS);
  const [notice, setNotice] = useState<{ message: string; type: 'success' | 'info' | 'warning' } | null>(null);

  const activePatient = patients.find((p) => p.id === selectedPatientId) || patients[0];

  const showToast = (message: string, type: 'success' | 'info' | 'warning' = 'success') => {
    setNotice({ message, type });
    setTimeout(() => {
      setNotice(null);
    }, 4000);
  };

  const handleSelectPatient = (id: string) => {
    setSelectedPatientId(id);
    setIsTakenOver(false);
    setIsSigned(false);
  };

  const handleToggleTakeover = () => {
    const nextState = !isTakenOver;
    setIsTakenOver(nextState);
    if (nextState) {
      showToast(`Đã tiếp quản ca bệnh ${activePatient.name}. AI đã tạm dừng sinh phản hồi tự động.`, 'warning');
    } else {
      showToast(`Đã trả quyền sinh câu trả lời tự động cho Trợ lý MedPaLM AI.`, 'info');
    }
  };

  const handleSendMessage = (text: string) => {
    const newMsg: ChatMessage = {
      id: `doc-${Date.now()}`,
      sender: 'doctor',
      senderName: 'BS. Nguyễn Phương Linh',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: text,
    };

    setPatients((prev) =>
      prev.map((p) =>
        p.id === activePatient.id
          ? {
              ...p,
              messages: [...p.messages, newMsg],
              lastSnippet: text,
              status: 'in_intervention',
            }
          : p
      )
    );

    if (!isTakenOver) {
      setIsTakenOver(true);
    }

    showToast('Đã gửi chỉ định lâm sàng trực tiếp tới bệnh nhân.', 'success');
  };

  const handleToggleProtocol = (protoId: string) => {
    setPatients((prev) =>
      prev.map((p) =>
        p.id === activePatient.id
          ? {
              ...p,
              protocols: p.protocols.map((proto) =>
                proto.id === protoId ? { ...proto, checked: !proto.checked } : proto
              ),
            }
          : p
      )
    );
  };

  const handleSignProtocol = () => {
    setIsSigned(true);
    showToast(`Đã ký số xác nhận phác đồ can thiệp lâm sàng cho ca ${activePatient.code} (BS. Nguyễn Phương Linh).`, 'success');
  };

  const handleEscalate = () => {
    navigate('/staff/queue');
  };

  const handleVideoCall = () => {
    showToast(`Đang khởi tạo phòng gọi khám video sơ bộ trực tiếp với bệnh nhân ${activePatient.name}...`, 'info');
  };

  const handleQuickAppointment = () => {
    navigate('/staff/doctor-schedule');
  };

  return (
    <div className="min-h-full flex flex-col bg-[#f8fafc] text-slate-800 font-sans p-4 xl:p-5">
      {/* SLA & Critical Status Banner */}
      <TopAlertBanner
        urgentCount={metrics.needTakeoverCount}
        slaTargetSeconds={metrics.slaTargetSeconds}
        slaCurrentSeconds={metrics.slaCurrentSeconds}
      />

      {/* Floating Toast Notification */}
      {notice && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-lg border text-xs font-bold flex items-center gap-2 animate-bounce ${
            notice.type === 'warning'
              ? 'bg-amber-600 text-white border-amber-700'
              : notice.type === 'info'
              ? 'bg-sky-700 text-white border-sky-800'
              : 'bg-emerald-700 text-white border-emerald-800'
          }`}
        >
          <span>{notice.message}</span>
        </div>
      )}

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 items-start w-full">
        {/* Left Column: Hàng đợi Giám sát */}
        <QueueSidebar
          patients={patients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={handleSelectPatient}
          metrics={metrics}
        />

        {/* Right Area: Spanning to the right edge */}
        <div className="flex-1 min-w-0 flex flex-col gap-3.5 w-full">
          {/* Top: PatientHeader stretches full width across to right border */}
          <PatientHeader
            patient={activePatient}
            isTakenOver={isTakenOver}
            onToggleTakeover={handleToggleTakeover}
            onEscalate={handleEscalate}
            onVideoCall={handleVideoCall}
            onQuickAppointment={handleQuickAppointment}
          />

          {/* Bottom Area: Khung Chat bên trái, Các khung sinh tồn/AI bên phải ngang hàng với khung chat */}
          <div className="flex flex-col xl:flex-row gap-3.5 items-start w-full">
            {/* Live Chat & Takeover Studio */}
            <main className="flex-1 min-w-0 w-full flex flex-col bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden h-[calc(100vh-250px)] min-h-[520px]">
              <MessageList messages={activePatient.messages} />

              <ChatInputArea
                patientName={activePatient.name}
                isTakenOver={isTakenOver}
                onSendMessage={handleSendMessage}
              />
            </main>

            {/* Real-time Telemetry & AI Clinical Support Column */}
            <aside className="w-full xl:w-80 2xl:w-88 shrink-0 flex flex-col gap-3 h-[calc(100vh-250px)] min-h-[520px] overflow-y-auto pr-0.5">
              <VitalsCard vitals={activePatient.vitals} />
              <AITriageCard triage={activePatient.triage} />
              <ProtocolCard
                protocols={activePatient.protocols}
                onToggleProtocol={handleToggleProtocol}
                onSignProtocol={handleSignProtocol}
                isSigned={isSigned}
              />
            </aside>
          </div>
        </div>
      </div>

      {/* Bottom Footer Metadata */}
      <FooterBar />
    </div>
  );
}
