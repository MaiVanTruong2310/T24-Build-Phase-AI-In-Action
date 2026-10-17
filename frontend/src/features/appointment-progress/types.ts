import { Booking, Doctor, Facility, MedicalService, Specialty } from '../appointment-booking/api';

export type BookingType = 'doctor_visit' | 'package' | 'coordination';

export type AppointmentFilter = 'all' | Exclude<Booking['status'], 'expired'>;

export interface AppointmentCatalog {
  doctors: Map<string, Doctor>;
  facilities: Map<string, Facility>;
  services: Map<string, MedicalService>;
  specialties: Map<string, Specialty>;
}

export interface ProgressStepInfo {
  steps: string[];
  currentStep: number;
  stepLabel: string;
  description: string;
}

export interface PreAppointmentInstruction {
  title: string;
  content: string;
  badge?: string;
  icon?: string;
}

export interface AppointmentDisplayData {
  bookingType: BookingType;
  typeBadge: {
    label: string;
    bg: string;
    text: string;
    border: string;
    icon: string;
  };
  primaryTitle: string;
  secondaryTitle: string;
  doctorName?: string | null;
  doctorTitle?: string | null;
  doctorAvatar?: string | null;
  specialtyName?: string | null;
  serviceName: string;
  servicePrice?: number | null;
  facilityName: string;
  preferredPeriod?: 'morning' | 'afternoon' | null;
  startsAtFormatted: string;
  endsAtFormatted?: string | null;
  instructions: PreAppointmentInstruction[];
  progress: ProgressStepInfo;
  notes?: string | null;
}

