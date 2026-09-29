import { fetchWithAuth } from '../../app/apiClient';

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
}

export type PatientProfileUpdate = Pick<
  PatientProfile,
  'full_name' | 'date_of_birth' | 'gender' | 'citizen_id' | 'health_insurance_code'
>;

export async function fetchCurrentUser(): Promise<PatientProfile> {
  const response = await fetchWithAuth('/users/me');
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || 'Không thể tải hồ sơ bệnh nhân');
  return payload.data;
}

export async function updateCurrentUser(update: PatientProfileUpdate): Promise<PatientProfile> {
  const response = await fetchWithAuth('/users/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || 'Không thể cập nhật hồ sơ bệnh nhân');
  return payload.data;
}
