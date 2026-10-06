export type PatientStatus = 'need_takeover' | 'in_intervention' | 'ai_handling';
export type PriorityLevel = 'critical' | 'high' | 'normal';
export type MessageSender = 'patient' | 'ai' | 'doctor';

export interface VitalsData {
  bloodPressure: string;
  bloodPressureStatus: string;
  heartRate: number;
  spO2: number;
  spO2Status: string;
  ecgLead: string;
  ecgStatus: string;
}

export interface AITriageData {
  confidence: number;
  differentialDiagnosis: string;
  riskFactors: string[];
}

export interface ProtocolItem {
  id: string;
  label: string;
  checked: boolean;
}

export interface ChatMessage {
  id: string;
  sender: MessageSender;
  senderName: string;
  time: string;
  badge?: string;
  content: string;
  alertBox?: {
    type: 'critical' | 'warning' | 'info';
    title: string;
    description: string;
  };
}

export interface PatientQueueItem {
  id: string;
  code: string; // e.g. "BN-2024-8831"
  name: string;
  age: number;
  gender: string;
  avatar: string;
  riskLevel: 'CAO' | 'TRUNG BÌNH' | 'THẤP';
  status: PatientStatus;
  timeAgo: string;
  priority: PriorityLevel;
  medicalHistory: string[];
  allergies: string[];
  categoryTag?: string;
  lastSnippet: string;
  subStatus?: string;
  confidence?: number;
  vitals: VitalsData;
  triage: AITriageData;
  protocols: ProtocolItem[];
  messages: ChatMessage[];
}

export interface HITLMetrics {
  totalQueue: number;
  needTakeoverCount: number;
  inInterventionCount: number;
  aiHandlingCount: number;
  slaTargetSeconds: number;
  slaCurrentSeconds: number;
  shiftAccuracyPercent: number;
  completedCasesCount: number;
  zeroDefectCount: number;
}
