import { fetchWithAuth } from '../../app/apiClient'

export interface StaffPatient {
  id: string
  full_name: string | null
  email: string | null
  phone: string | null
  status: string
  gender: string | null
  created_at: string
}

export interface StaffPatientPage {
  items: StaffPatient[]
  total: number
  offset: number
  limit: number
}

export interface StaffPatientDetail extends Omit<StaffPatient, 'created_at'> {
  date_of_birth: string | null
  citizen_id_masked: string | null
  health_insurance_code_masked: string | null
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetchWithAuth(path, { signal })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.message || payload.detail || 'Không thể tải dữ liệu bệnh nhân.')
  return payload.data as T
}

export function fetchStaffPatients(params: URLSearchParams, signal?: AbortSignal): Promise<StaffPatientPage> {
  return request(`/staff/patients?${params.toString()}`, signal)
}

export function fetchStaffPatient(id: string, signal?: AbortSignal): Promise<StaffPatientDetail> {
  return request(`/staff/patients/${encodeURIComponent(id)}`, signal)
}
