import { AUTH_TOKENS_UPDATED_EVENT } from '../features/auth/session'

export interface CachedApiResponse {
  key: string
  ownerId: string
  body: string
  status: number
  statusText: string
  contentType: string
  expiresAt: number
}

interface CacheBridge {
  get: (key: string) => CachedApiResponse | undefined
  set: (entry: CachedApiResponse) => void
  remove: (key: string) => void
  clear: () => void
  ownerId: () => string | null
}

let bridge: CacheBridge | undefined
let generation = 0

export function configureApiResponseCache(value: CacheBridge): void {
  bridge = value
  if (typeof window !== 'undefined') window.addEventListener(AUTH_TOKENS_UPDATED_EVENT, clearCachedApiResponses)
}

export function apiCacheOwner(): string | null {
  return bridge?.ownerId() ?? null
}

export function apiCacheGeneration(): number {
  return generation
}

export function readCachedApiResponse(key: string): CachedApiResponse | undefined {
  const entry = bridge?.get(key)
  if (!entry) return undefined
  if (entry.ownerId !== bridge?.ownerId() || entry.expiresAt <= Date.now()) {
    bridge?.remove(key)
    return undefined
  }
  return entry
}

export function saveCachedApiResponse(entry: CachedApiResponse, expectedGeneration: number): void {
  if (generation === expectedGeneration && entry.ownerId === bridge?.ownerId()) bridge?.set(entry)
}

export function clearCachedApiResponses(): void {
  generation += 1
  bridge?.clear()
}

