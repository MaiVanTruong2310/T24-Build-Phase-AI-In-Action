import * as E from 'fp-ts/Either';
import { fetchWithAuth } from '../../app/apiClient';

export interface Service {
  id: string;
  code: string;
  name: string;
  description: string | null;
  duration_minutes: number | null;
  price: number | null;
  original_price: number | null;
  category: string | null;
  features: string[] | null;
  patient_count: number | null;
  satisfaction_rate: number | null;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}

export interface CreateServicePayload {
  code: string;
  name: string;
  description?: string;
  duration_minutes?: number;
  price?: number;
  original_price?: number;
  category?: string;
  features?: string[];
}



export const fetchServices = () => async (): Promise<E.Either<Error, Service[]>> => {
  try {
    const response = await fetchWithAuth('/api/v1/staff/services');
    if (!response.ok) {
      throw new Error(`Failed to fetch services: ${response.statusText}`);
    }
    const json = await response.json();
    return E.right((json.data || []) as Service[]);
  } catch (error) {
    return E.left(error instanceof Error ? error : new Error('Unknown error'));
  }
};

export const createService = (payload: CreateServicePayload) => async (): Promise<E.Either<Error, Service>> => {
  try {
    const response = await fetchWithAuth('/api/v1/staff/services', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Failed to create service: ${response.statusText}`);
    }
    const json = await response.json();
    return E.right(json.data as Service);
  } catch (error) {
    return E.left(error instanceof Error ? error : new Error('Unknown error'));
  }
};
