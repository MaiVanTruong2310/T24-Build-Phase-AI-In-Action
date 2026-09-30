// ─── Patient Core ────────────────────────────────────────────────
export interface Patient {
  id: string;
  code: string; // e.g. "BN-98041"
  fullName: string;
  avatarUrl: string;
  gender: 'Nam' | 'Nữ' | 'Khác';
  age: number;
  dateOfBirth: string; // ISO date
  bloodType: string;
  insuranceId: string; // BHYT
  allergyNote: string | null; // e.g. "Dị ứng: Penicillin"
  status: 'active' | 'inactive';
  activeDate: string; // last active
}

// ─── Patient Info Bar ────────────────────────────────────────────
export interface PatientInfoItem {
  label: string;
  value: string;
  icon?: string;
}

// ─── Vital Signs ─────────────────────────────────────────────────
export type VitalStatus = 'normal' | 'warning' | 'critical';

export interface VitalSign {
  id: string;
  icon: string;
  label: string;
  value: string;
  unit: string;
  status: VitalStatus;
  statusLabel: string;
  trend: 'up' | 'down' | 'stable';
  trendData: number[];
  referenceRange?: string;
}

// ─── Medical Tab ─────────────────────────────────────────────────
export type MedicalTabKey =
  | 'history'
  | 'prescriptions'
  | 'tests'
  | 'timeline';

export interface MedicalTab {
  key: MedicalTabKey;
  label: string;
  count?: number;
}

// ─── Medical Timeline ────────────────────────────────────────────
export type TimelineEntryType =
  | 'examination'
  | 'health-check';

export interface Prescription {
  id: string;
  code: string;
  detail: string; // e.g. "3 loại thuốc × 7 ngày"
}

export interface ExaminationDetail {
  title: string;
  description: string;
}

export interface TestResult {
  id: string;
  title: string;
  description: string;
  hasImageLink: boolean;
  imageLinkLabel?: string;
}

export interface TimelineEntry {
  id: string;
  type: TimelineEntryType;
  badgeLabel: string;
  badgeColor: 'teal' | 'blue' | 'amber';
  title: string;
  date: string;
  time?: string;
  hitlBadge?: string;
  doctorName: string;
  doctorDepartment: string;
  doctorCode?: string;
  summary?: string;
  prescription?: Prescription;
  prescriptionNote?: string;
  findings?: ExaminationDetail[];
  testResults?: TestResult[];
  recommendation?: string;
  resultType?: string;
  resultLabel?: string;
  additionalLinks?: { label: string; url: string }[];
}

// ─── Emergency Contact Form ──────────────────────────────────────
export interface EmergencyContact {
  fullName: string;
  relationship: string;
  phone: string;
  healthIdCode: string; // Mã YT (Bác sĩ)
  currentMedications: string;
  address: string;
}

// ─── Page-level Aggregate ────────────────────────────────────────
export interface PatientProfileData {
  patient: Patient;
  infoBar: PatientInfoItem[];
  vitalSigns: VitalSign[];
  medicalTabs: MedicalTab[];
  timeline: TimelineEntry[];
  emergencyContact: EmergencyContact;
}
