import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { resolveTakeoverWebSocketUrl, claimTakeoverCase, fetchTakeoverCase, fetchTakeoverCases, releaseTakeoverCase, resolveTakeoverCase, sendTakeoverMessage, type TakeoverCase, type TakeoverCaseDetail } from './api';
import { websocketNeedsTicket } from '../../app/apiClient';
import { fetchTakeoverTicket } from '../../features/chat/api';
import { PatientQueueItem, ChatMessage, HITLMetrics } from './types';
import { TopAlertBanner } from './components/TopAlertBanner';
import { QueueSidebar } from './components/QueueSidebar';
import { PatientHeader } from './components/PatientHeader';
import { MessageList } from './components/MessageList';
import { ChatInputArea } from './components/ChatInputArea';
import { VitalsCard } from './components/VitalsCard';
import { AITriageCard } from './components/AITriageCard';
import { ProtocolCard } from './components/ProtocolCard';
import { FooterBar } from './components/FooterBar';

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function formatAge(value: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return 'vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  return `${Math.round(minutes / 60)} giờ trước`;
}

function toMessages(detail: TakeoverCaseDetail): ChatMessage[] {
  return detail.messages.map((message) => ({
    id: message.id,
    sender: message.author_type === 'patient' ? 'patient' : message.author_type === 'staff' ? 'doctor' : 'ai',
    senderName: message.author_type === 'patient' ? detail.case.summary.patient_name || 'Bệnh nhân' : message.author_type === 'staff' ? 'Nhân viên y tế' : 'VCare+ AI',
    time: formatTime(message.created_at),
    content: message.content,
  }));
}

function toQueueItem(item: TakeoverCase, messages: ChatMessage[] = []): PatientQueueItem {
  const summary = item.summary || {};
  const priority = item.priority === 'critical' ? 'critical' : item.priority === 'high' ? 'high' : 'normal';
  const status = item.status === 'taken_over' ? 'in_intervention' : item.status === 'resolved' ? 'ai_handling' : 'need_takeover';
  return {
    id: item.id,
    code: `HITL-${item.id.slice(0, 8).toUpperCase()}`,
    name: summary.patient_name || 'Bệnh nhân',
    age: summary.patient_age || 0,
    gender: summary.patient_gender || 'Chưa rõ',
    avatar: '',
    riskLevel: item.priority === 'critical' ? 'CAO' : item.priority === 'high' ? 'TRUNG BÌNH' : 'THẤP',
    status,
    timeAgo: formatAge(item.created_at),
    priority,
    medicalHistory: [],
    allergies: [],
    categoryTag: summary.suggested_department || undefined,
    lastSnippet: summary.patient_message || 'Ca chat đang chờ nhân viên tiếp nhận.',
    subStatus: item.status === 'taken_over' ? 'Đang được tiếp quản' : item.status === 'resolved' ? 'Đã xử lý' : 'Chờ tiếp nhận',
    confidence: summary.ats_level ? Math.max(0, 100 - summary.ats_level * 10) : undefined,
    vitals: {
      bloodPressure: 'Chưa có',
      bloodPressureStatus: 'Chưa ghi nhận',
      heartRate: 0,
      spO2: 0,
      spO2Status: 'Chưa ghi nhận',
      ecgLead: 'Chưa có dữ liệu',
      ecgStatus: 'Chưa ghi nhận',
    },
    triage: {
      confidence: summary.ats_level ? Math.max(0, 100 - summary.ats_level * 10) : 0,
      differentialDiagnosis: 'Không chẩn đoán tự động; cần staff tiếp nhận.',
      riskFactors: [summary.workflow_status || 'HUMAN_HELP_REQUESTED'],
    },
    protocols: [],
    messages,
  };
}

function metrics(cases: TakeoverCase[]): HITLMetrics {
  return {
    totalQueue: cases.length,
    needTakeoverCount: cases.filter((item) => item.status === 'queued' || item.status === 'released').length,
    inInterventionCount: cases.filter((item) => item.status === 'taken_over').length,
    aiHandlingCount: 0,
    slaTargetSeconds: 90,
    slaCurrentSeconds: 0,
    shiftAccuracyPercent: 0,
    completedCasesCount: cases.filter((item) => item.status === 'resolved').length,
    zeroDefectCount: 0,
  };
}

export default function ChatTakeover() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<TakeoverCase[]>([]);
  const [activeDetail, setActiveDetail] = useState<TakeoverCaseDetail | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const queueRequestRef = useRef<Promise<TakeoverCase[]> | null>(null);

  const showToast = useCallback((message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 4000);
  }, []);

  const loadQueue = useCallback(async (signal?: AbortSignal) => {
    setError('');
    try {
      // React StrictMode intentionally mounts effects twice in development.
      // Share the first in-flight request instead of aborting it during the
      // first effect cleanup and issuing a second request immediately after.
      const request = queueRequestRef.current ?? fetchTakeoverCases();
      queueRequestRef.current = request;
      const nextCases = await request;
      if (!signal?.aborted) setCases(nextCases);
      if (queueRequestRef.current === request) queueRequestRef.current = null;
    } catch (cause) {
      if (!signal?.aborted) setError(cause instanceof Error ? cause.message : 'Không thể tải hàng đợi takeover.');
      queueRequestRef.current = null;
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string, signal?: AbortSignal) => {
    try {
      const detail = await fetchTakeoverCase(id, signal);
      if (!signal?.aborted) setActiveDetail(detail);
    } catch (cause) {
      if (!signal?.aborted) setError(cause instanceof Error ? cause.message : 'Không thể tải ca takeover.');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadQueue(controller.signal);
    return () => controller.abort();
  }, [loadQueue]);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | undefined;
    let keepalive: number | undefined;
    // WebSocket khác domain (proxy same-origin) không mang cookie → xác thực bằng ticket.
    void (websocketNeedsTicket ? fetchTakeoverTicket() : Promise.resolve(null)).then((ticket) => {
      if (cancelled) return;
      const current = new WebSocket(resolveTakeoverWebSocketUrl(undefined, ticket));
      socket = current;
      keepalive = window.setInterval(() => {
        if (current.readyState === WebSocket.OPEN) current.send('keepalive');
      }, 20_000);
      current.onmessage = () => void loadQueue();
      current.onerror = () => current.close();
    });
    return () => {
      cancelled = true;
      window.clearInterval(keepalive);
      socket?.close();
    };
  }, [loadQueue]);

  useEffect(() => {
    if (!selectedCaseId) return;
    const controller = new AbortController();
    void loadDetail(selectedCaseId, controller.signal);
    return () => controller.abort();
  }, [loadDetail, selectedCaseId]);

  const patients = useMemo(
    () => cases.map((item) => toQueueItem(item, item.id === activeDetail?.case.id ? toMessages(activeDetail) : [])),
    [activeDetail, cases],
  );
  const activePatient = activeDetail ? toQueueItem(activeDetail.case, toMessages(activeDetail)) : null;
  const isTakenOver = activeDetail?.case.status === 'taken_over';
  const activeCaseId = activeDetail?.case.id;
  const activeSessionId = activeDetail?.case.session_id;

  useEffect(() => {
    if (!activeCaseId || !activeSessionId) return;
    let cancelled = false;
    let socket: WebSocket | undefined;
    void (websocketNeedsTicket ? fetchTakeoverTicket() : Promise.resolve(null)).then((ticket) => {
      if (cancelled) return;
      const current = new WebSocket(resolveTakeoverWebSocketUrl(activeSessionId, ticket));
      socket = current;
      current.onmessage = () => void loadDetail(activeCaseId);
      current.onerror = () => current.close();
    });
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [activeCaseId, activeSessionId, loadDetail]);

  const handleToggleTakeover = async () => {
    if (!activeDetail) return;
    try {
      const updated = isTakenOver
        ? await releaseTakeoverCase(activeDetail.case.id)
        : await claimTakeoverCase(activeDetail.case.id);
      setActiveDetail((current) => current ? { ...current, case: updated } : current);
      setCases((current) => current.map((item) => item.id === updated.id ? updated : item));
      showToast(isTakenOver ? 'Đã trả ca về hàng đợi.' : 'Đã tiếp quản ca chat.');
    } catch (cause) {
      showToast(cause instanceof Error ? cause.message : 'Không thể cập nhật trạng thái takeover.');
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!activeDetail || !isTakenOver) return;
    try {
      await sendTakeoverMessage(activeDetail.case.id, text, crypto.randomUUID());
      await loadDetail(activeDetail.case.id);
      showToast('Đã gửi tin nhắn trực tiếp tới bệnh nhân.');
    } catch (cause) {
      showToast(cause instanceof Error ? cause.message : 'Không thể gửi tin nhắn.');
    }
  };

  const handleResolve = async () => {
    if (!activeDetail || !isTakenOver) return;
    try {
      const updated = await resolveTakeoverCase(activeDetail.case.id);
      setActiveDetail((current) => current ? { ...current, case: updated } : current);
      setCases((current) => current.map((item) => item.id === updated.id ? updated : item));
      showToast('Đã đánh dấu ca takeover đã xử lý.');
    } catch (cause) {
      showToast(cause instanceof Error ? cause.message : 'Không thể đóng ca takeover.');
    }
  };

  if (loading) return <div className="flex min-h-full items-center justify-center bg-slate-50 text-slate-600">Đang tải hàng đợi takeover…</div>;

  return (
    <div className="min-h-full flex flex-col bg-[#f8fafc] text-slate-800 font-sans p-4 xl:p-5">
      <TopAlertBanner urgentCount={metrics(cases).needTakeoverCount} slaTargetSeconds={90} slaCurrentSeconds={0} />
      {notice && <div className="fixed bottom-6 right-6 z-50 rounded-xl bg-slate-800 px-4 py-3 text-xs font-bold text-white shadow-lg">{notice}</div>}
      {error && <div role="alert" className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 items-start w-full">
        <QueueSidebar patients={patients} selectedPatientId={activeDetail?.case.id || ''} onSelectPatient={setSelectedCaseId} metrics={metrics(cases)} />
        {activePatient && activeDetail ? (
          <div className="flex-1 min-w-0 flex flex-col gap-3.5 w-full">
            <PatientHeader patient={activePatient} isTakenOver={Boolean(isTakenOver)} onToggleTakeover={() => void handleToggleTakeover()} onResolve={() => void handleResolve()} onEscalate={() => navigate('/staff/queue')} onVideoCall={() => showToast('Video call chưa thuộc MVP takeover.')} onQuickAppointment={() => navigate('/staff/doctor-schedule')} />
            <div className="flex flex-col xl:flex-row gap-3.5 items-start w-full">
              <main className="flex-1 min-w-0 w-full flex flex-col bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden h-[calc(100vh-250px)] min-h-[520px]">
                <MessageList messages={activePatient.messages} />
                <ChatInputArea patientName={activePatient.name} isTakenOver={Boolean(isTakenOver)} onSendMessage={(text) => void handleSendMessage(text)} />
              </main>
              <aside className="w-full xl:w-80 2xl:w-88 shrink-0 flex flex-col gap-3 h-[calc(100vh-250px)] min-h-[520px] overflow-y-auto pr-0.5">
                <VitalsCard vitals={activePatient.vitals} />
                <AITriageCard triage={activePatient.triage} />
                <ProtocolCard protocols={activePatient.protocols} onToggleProtocol={() => undefined} onSignProtocol={() => undefined} isSigned={false} />
              </aside>
            </div>
          </div>
        ) : (
          <div className="flex min-h-[520px] flex-1 items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white text-sm text-slate-500">Chọn một ca trong hàng đợi để bắt đầu takeover.</div>
        )}
      </div>
      <FooterBar />
    </div>
  );
}
