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
  experience_years?: number | null;
  specialty_ids?: string[];
  specialties?: Array<{ specialty?: { name: string } | null }>;
  facilities?: Array<{ facility?: { name: string } | null }>;
  services?: Array<{ service?: { name: string } | null }>;
  status: string;
  booking_enabled: boolean;
}

export interface StaffDoctor {
  id: string
  code: string
  full_name: string
  title?: string | null
  professional_role: string
  bio?: string | null
  honors: string[]
  academic_ranks: string[]
  degrees: string[]
  languages: string[]
  experience_years?: number | null
  position?: string | null
  education: string[]
  work_history: string[]
  awards: string[]
  specialties: Array<{ specialty?: { name: string } | null }>
  specialty_ids: string[]
  facilities: Array<{ facility_id: string; department?: string | null; room?: string | null; position?: string | null; active_from?: string | null; active_to?: string | null; is_primary?: boolean; facility?: { name: string } | null }>
  status: string
  booking_enabled: boolean
}

export async function fetchStaffDoctors(filters: { name?: string; specialtyId?: string; facilityId?: string; offset?: number; limit?: number } = {}): Promise<StaffDoctor[]> {
  const query = new URLSearchParams()
  if (filters.name) query.set('name', filters.name)
  if (filters.specialtyId) query.set('specialty_id', filters.specialtyId)
  if (filters.facilityId) query.set('facility_id', filters.facilityId)
  if (filters.offset) query.set('offset', String(filters.offset))
  if (filters.limit) query.set('limit', String(filters.limit))
  const response = await fetchWithAuth(`/api/v1/staff/doctors?${query}`)
  if (!response.ok) throw new Error(`Không thể tải bác sĩ (${response.status})`)
  const json = await response.json() as { data: StaffDoctor[] }
  return json.data || []
}

export async function fetchStaffDoctor(id: string): Promise<StaffDoctor> {
  const response = await fetchWithAuth(`/api/v1/staff/doctors/${id}`)
  if (!response.ok) throw new Error('Không thể tải hồ sơ bác sĩ')
  const json = await response.json() as { data: StaffDoctor }
  return json.data
}

export async function updateStaffDoctor(id: string, payload: Record<string, unknown>): Promise<void> {
  const response = await fetchWithAuth(`/api/v1/staff/doctors/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`Không thể lưu hồ sơ bác sĩ (${response.status})`)
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
      const response = await fetchWithAuth('/api/v1/staff/doctors');
      if (!response.ok) {
        throw new Error(`Failed to fetch doctors: ${response.statusText}`);
      }
      const json = await response.json() as { data: DoctorApiRecord[] };
      return json.data.map((doc) => ({
        id: doc.id,
        name: doc.full_name,
        title: doc.title || 'Doctor',
        experienceYears: doc.experience_years ?? 0,
        avatarUrl: doc.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(doc.full_name)}`,
        licenseNumber: doc.license_number || '',
        specialty: doc.specialties?.map((item) => item.specialty?.name).filter(Boolean).join(', ')
          || (doc.specialty_ids?.length ? 'Specialty Assigned' : 'General'),
        facility: doc.facilities?.map((item) => item.facility?.name).filter(Boolean).join(', ')
          || 'Unassigned',
        casesMonth: 0,
        clinicalMetric: 'N/A',
        rating: 0,
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
