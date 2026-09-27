export type RemoteData<E, A> =
  | { _tag: 'NotAsked' }
  | { _tag: 'Loading' }
  | { _tag: 'Failure'; error: E }
  | { _tag: 'Success'; value: A };

export const notAsked = <E, A>(): RemoteData<E, A> => ({ _tag: 'NotAsked' });
export const loading = <E, A>(): RemoteData<E, A> => ({ _tag: 'Loading' });
export const failure = <E, A>(error: E): RemoteData<E, A> => ({ _tag: 'Failure', error });
export const success = <E, A>(value: A): RemoteData<E, A> => ({ _tag: 'Success', value });

export const foldRemoteData = <E, A, R>(
  data: RemoteData<E, A>,
  onNotAsked: () => R,
  onLoading: () => R,
  onFailure: (error: E) => R,
  onSuccess: (value: A) => R
): R => {
  switch (data._tag) {
    case 'NotAsked': return onNotAsked();
    case 'Loading': return onLoading();
    case 'Failure': return onFailure(data.error);
    case 'Success': return onSuccess(data.value);
  }
};
