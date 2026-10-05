import { AUTH_TOKENS_UPDATED_EVENT, readPublishedSession } from '../features/auth/session';

type Entry<T> = {
  value?: T;
  expiresAt: number;
  pending?: Promise<T>;
};

const entries = new Map<string, Entry<unknown>>();
let ownerId: string | null = null;

function currentOwner(): string | null {
  const current = readPublishedSession()?.id ?? null;
  if (current !== ownerId) {
    entries.clear();
    ownerId = current;
  }
  return current;
}

if (typeof window !== 'undefined') {
  window.addEventListener(AUTH_TOKENS_UPDATED_EVENT, currentOwner);
}

export function peekQuery<T>(key: string, allowStale = false): T | undefined {
  if (!currentOwner()) return undefined;
  const entry = entries.get(key) as Entry<T> | undefined;
  return entry && (allowStale || entry.expiresAt > Date.now()) ? entry.value : undefined;
}

export function rememberQuery<T>(key: string, value: T, ttlMs: number): void {
  if (!currentOwner()) return;
  entries.set(key, { value, expiresAt: Date.now() + ttlMs });
}

export function cachedQuery<T>(key: string, ttlMs: number, load: () => Promise<T>): Promise<T> {
  const owner = currentOwner();
  if (!owner) return load();
  const previous = entries.get(key) as Entry<T> | undefined;
  if (previous?.value !== undefined && previous.expiresAt > Date.now()) {
    return Promise.resolve(previous.value);
  }
  if (previous?.pending) return previous.pending;

  const entry: Entry<T> = { expiresAt: 0 };
  const pending = load().then(
    (value) => {
      if (currentOwner() === owner && entries.get(key) === entry) {
        entries.set(key, { value, expiresAt: Date.now() + ttlMs });
      }
      return value;
    },
    (error: unknown) => {
      if (entries.get(key) === entry) entries.delete(key);
      throw error;
    },
  );
  entry.pending = pending;
  entries.set(key, entry);
  return pending;
}
