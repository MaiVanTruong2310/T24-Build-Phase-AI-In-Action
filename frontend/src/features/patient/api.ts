import { fetchWithAuth } from '../../app/apiClient';
import { cachedQuery, peekQuery, rememberQuery } from '../../app/queryCache';

const PROFILE_KEY = 'patient-profile';
const PROFILE_TTL_MS = 30_000;

export interface PatientProfile {
  id: string;
  email: string | null;
  phone: string | null;
  role: 'patient' | 'staff';
  status: string;
  full_name: string | null;
  date_of_birth: string | null;
  gender: 'male' | 'female' | 'other' | 'unspecified' | null;
  citizen_id: string | null;
  health_insurance_code: string | null;
  patient_details?: PatientDetails | null;
}

export interface MedicalCondition {
  id: string;
  name: string;
  status: 'recovered' | 'in_treatment';
}

export interface PatientDetails {
  medical_history?: MedicalCondition[];
  blood_type?: string | null;
  allergies?: string | null;
  current_medications?: string | null;
  address?: string | null;
  emergency_name?: string | null;
  emergency_relationship?: string | null;
  emergency_phone?: string | null;
  systolic?: number | null;
  diastolic?: number | null;
  heart_rate?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  blood_glucose?: number | null;
}

export type PatientProfileUpdate = Partial<Pick<
  PatientProfile,
  'full_name' | 'phone' | 'date_of_birth' | 'gender' | 'citizen_id' | 'health_insurance_code' | 'patient_details'
>>;

export async function fetchCurrentUser(): Promise<PatientProfile> {
  return cachedQuery(PROFILE_KEY, PROFILE_TTL_MS, async () => {
    const response = await fetchWithAuth('/users/me');
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || 'Không thể tải hồ sơ bệnh nhân');
    return payload.data as PatientProfile;
  });
}

export function peekCurrentUser(): PatientProfile | undefined {
  return peekQuery<PatientProfile>(PROFILE_KEY, true);
}

export async function updateCurrentUser(update: PatientProfileUpdate): Promise<PatientProfile> {
  const response = await fetchWithAuth('/users/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || 'Không thể cập nhật hồ sơ bệnh nhân');
  rememberQuery(PROFILE_KEY, payload.data as PatientProfile, PROFILE_TTL_MS);
  return payload.data;
}
