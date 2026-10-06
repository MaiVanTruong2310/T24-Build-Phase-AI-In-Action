import { fetchWithAuth } from '../../app/apiClient'

export interface PatientProfile {
  id: string; full_name: string; date_of_birth: string | null; gender: string | null;
  contact_phone: string | null; citizen_id: string | null; health_insurance_code: string | null;
  address: string | null; relationship: string; is_self: boolean; status: string;
}
export interface RelativeInput {
  full_name: string; date_of_birth: string; gender: string; relationship: string;
  contact_phone: string; citizen_id?: string; health_insurance_code?: string; address?: string;
  consent_to_manage: boolean;
}
async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetchWithAuth('/patient-profiles' + path, {
    method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined,
  })
  const result = await response.json()
  if (!response.ok) throw new Error(result.message || result.detail || 'Không thể xử lý hồ sơ người khám.')
  return result.data as T
}
export const fetchPatientProfiles = () => api<PatientProfile[]>('')
export const addPatientProfile = (body: RelativeInput) => api<PatientProfile>('', 'POST', body)
export const editPatientProfile = (id: string, body: RelativeInput) => api<PatientProfile>('/' + id, 'PATCH', body)
export const archivePatientProfile = (id: string) => api<void>('/' + id, 'DELETE')
export const relationshipNames: Record<string, string> = { self: 'Bản thân', parent: 'Cha/mẹ', child: 'Con', spouse: 'Vợ/chồng', sibling: 'Anh/chị/em', grandparent: 'Ông/bà', other: 'Khác' }
