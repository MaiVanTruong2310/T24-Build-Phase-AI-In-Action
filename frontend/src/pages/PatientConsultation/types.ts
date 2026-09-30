export interface MatchedDoctor {
  id: string;
  name: string;
  title: string;
  specialty: string;
  rating: number;
  reviewsCount: number;
  avatarUrl: string;
  nextSlot: string;
  isPriority?: boolean;
}

export interface ProposedAppointment {
  doctorName: string;
  doctorAvatarUrl: string;
  specialty: string;
  timeSlot: string;
  location: string;
  serviceType: string;
  fee: string;
  insuranceNote: string;
  priorityLabel: string;
}

export interface VitalItem {
  id: string;
  label: string;
  value: string;
  unit?: string;
  status: string;
  statusType: 'warning' | 'normal' | 'critical';
}

export interface ConsultationData {
  assessmentTitle: string;
  lastUpdated: string;
  statusText: string;
  symptoms: {
    title: string;
    verifiedBadge: string;
    description: string;
  };
  doctorReview: {
    doctorName: string;
    doctorTitle: string;
    avatarUrl: string;
    note: string;
  };
  matchedDoctors: MatchedDoctor[];
  proposedAppointment: ProposedAppointment;
  vitals: VitalItem[];
}
