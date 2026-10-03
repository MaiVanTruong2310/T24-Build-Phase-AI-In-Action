export interface KPICardData {
  id: string;
  title: string;
  value: string | number;
  unit: string;
  badgeText?: string;
  badgeType?: 'danger' | 'warning' | 'info' | 'success';
  trendText?: string;
  actionText: string;
  actionLink: string;
  variant: 'normal' | 'critical' | 'warning' | 'success';
}

export type UrgentPriority = 'critical' | 'clinical_warning' | 'low_confidence' | 'reschedule';

export interface UrgentCaseItem {
  id: string;
  patientName: string;
  age: number;
  gender: 'Nam' | 'Nữ';
  priorityBadge: string;
  priorityType: UrgentPriority;
  alertText: string;
  sourceText: string;
  actionLabel: string;
  actionLink: string;
  actionType: 'escalate' | 'approve' | 'takeover' | 'reschedule';
  avatar?: string;
}

export interface OnDutyDoctor {
  id: string;
  name: string;
  title: string;
  specialty: string;
  room: string;
  waitingCount: number;
  status: 'Đang khám' | 'Sẵn sàng' | 'Nghỉ giải lao';
  avatar: string;
}

export interface AuditLogItem {
  id: string;
  time: string;
  actor: string;
  action: string;
  highlightCode?: string;
  isCritical?: boolean;
}

export interface HourlyTrafficBar {
  hour: string;
  aiHandledPercent: number;
  hitlHandledPercent: number;
  aiHeightPercent: number;
  hitlHeightPercent: number;
  isCurrent?: boolean;
  isProjected?: boolean;
}
