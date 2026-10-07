import { Booking, Doctor, Facility, MedicalService, Specialty } from '../appointment-booking/api';

export type AppointmentFilter = 'all' | Exclude<Booking['status'], 'expired'>;

export interface AppointmentCatalog {
  doctors: Map<string, Doctor>;
  facilities: Map<string, Facility>;
  services: Map<string, MedicalService>;
  specialties: Map<string, Specialty>;
}

export interface AppointmentDisplayData {
  doctorName: string;
  doctorTitle: string;
  doctorAvatar: string | null;
  specialtyName: string;
  serviceName: string;
  facilityName: string;
}
