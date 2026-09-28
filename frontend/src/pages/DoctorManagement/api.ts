import * as TE from 'fp-ts/TaskEither';
import { Doctor } from './types';
import { fetchWithAuth } from '../../app/apiClient';

export interface Specialty {
  id: string;
  name: string;
}

interface DoctorApiRecord {
  id: string;
  full_name: string;
  title?: string | null;
  avatar_url?: string | null;
  license_number?: string | null;
  specialty_ids?: string[];
  facilities?: unknown[];
  status: string;
  booking_enabled: boolean;
}

interface SpecialtyApiRecord {
  id: string;
  name: string;
}

export type CreateDoctorPayload = Record<string, unknown>;

// Fallback mock data in case of empty fields
const mapStatus = (status: string, bookingEnabled: boolean): Doctor['status'] => {
  if (!bookingEnabled) return 'leave';
  if (status === 'active') return 'ready';
  return 'examining';
};

export const fetchDoctors = (): TE.TaskEither<Error, Doctor[]> => 
  TE.tryCatch(
    async () => {
      const response = await fetchWithAuth('/api/v1/doctors');
      if (!response.ok) {
        throw new Error(`Failed to fetch doctors: ${response.statusText}`);
      }
      const json = await response.json() as { data: DoctorApiRecord[] };
      return json.data.map((doc) => ({
        id: doc.id,
        name: doc.full_name,
        title: doc.title || 'Doctor',
        experienceYears: 0, // Fallback as not in backend
        avatarUrl: doc.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(doc.full_name)}`,
        licenseNumber: doc.license_number || '',
        specialty: doc.specialty_ids?.length ? 'Specialty Assigned' : 'General', // Would need a separate fetch for names
        facility: doc.facilities?.length ? 'Facility Assigned' : 'Unassigned',
        casesMonth: 0,
        clinicalMetric: 'N/A',
        rating: 5.0,
        reviewCount: 0,
        status: mapStatus(doc.status, doc.booking_enabled),
      }));
    },
    (reason) => new Error(String(reason))
  );

export const fetchSpecialties = (): TE.TaskEither<Error, Specialty[]> =>
  TE.tryCatch(
    async () => {
      const response = await fetchWithAuth('/api/v1/specialties');
      if (!response.ok) {
        throw new Error(`Failed to fetch specialties: ${response.statusText}`);
      }
      const json = await response.json() as { data: SpecialtyApiRecord[] };
      return json.data.map((spec) => ({
        id: spec.id,
        name: spec.name,
      }));
    },
    (reason) => new Error(String(reason))
  );

export const createDoctor = (payload: CreateDoctorPayload): TE.TaskEither<Error, void> =>
  TE.tryCatch(
    async () => {
      const response = await fetchWithAuth('/api/v1/staff/doctors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to create doctor: ${response.statusText}`);
      }
    },
    (reason) => new Error(String(reason))
  );
