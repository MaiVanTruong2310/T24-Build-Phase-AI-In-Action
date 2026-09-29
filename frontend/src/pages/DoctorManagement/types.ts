export interface Doctor {
  id: string;
  name: string;
  title: string;
  experienceYears: number;
  avatarUrl: string;
  licenseNumber: string;
  specialty: string;
  facility: string;
  casesMonth: number;
  clinicalMetric: string;
  rating: number;
  reviewCount: number;
  status: 'ready' | 'examining' | 'emergency' | 'full' | 'leave';
  isHitlLead?: boolean;
}

export type RemoteData<E, A> =
  | { _tag: 'NotAsked' }
  | { _tag: 'Loading' }
  | { _tag: 'Failure'; error: E }
  | { _tag: 'Success'; data: A };

export const notAsked = <E, A>(): RemoteData<E, A> => ({ _tag: 'NotAsked' });
export const loading = <E, A>(): RemoteData<E, A> => ({ _tag: 'Loading' });
export const failure = <E, A>(error: E): RemoteData<E, A> => ({ _tag: 'Failure', error });
export const success = <E, A>(data: A): RemoteData<E, A> => ({ _tag: 'Success', data });

export function foldRemoteData<E, A, R>(
  rd: RemoteData<E, A>,
  onNotAsked: () => R,
  onLoading: () => R,
  onFailure: (e: E) => R,
  onSuccess: (a: A) => R
): R {
  switch (rd._tag) {
    case 'NotAsked': return onNotAsked();
    case 'Loading': return onLoading();
    case 'Failure': return onFailure(rd.error);
    case 'Success': return onSuccess(rd.data);
  }
}
