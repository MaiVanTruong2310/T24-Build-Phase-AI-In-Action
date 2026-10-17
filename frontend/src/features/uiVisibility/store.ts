// Trạng thái ẩn/hiện thành phần giao diện (GET /ui-visibility công khai; PUT chỉ admin).
// Nhớ bản gần nhất vào localStorage để lần tải sau không nháy thành phần đã ẩn.
import { useSyncExternalStore } from 'react';
import { fetchPublicApi, fetchWithAuth } from '../../app/apiClient';

const CACHE_KEY = 'vcare_ui_hidden';
const EDIT_KEY = 'vcare_ui_edit';
const ROLE_KEY = 'vcare_ui_preview_role';
export const UI_CHANGED_MESSAGE = 'vcare:ui-visibility-changed';

function readCache(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(CACHE_KEY) || '[]') as string[]);
  } catch {
    return new Set();
  }
}

let hidden = readCache();
let version = 0;
const listeners = new Set<() => void>();

function setHidden(keys: string[]) {
  hidden = new Set(keys);
  version += 1;
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(keys)); } catch { /* chặn lưu trữ: dùng bản trong bộ nhớ */ }
  listeners.forEach((listener) => listener());
}

export async function refreshUiVisibility(): Promise<void> {
  try {
    const response = await fetchPublicApi('/ui-visibility');
    if (!response.ok) return;
    const payload = await response.json();
    if (Array.isArray(payload?.data?.hidden)) setHidden(payload.data.hidden);
  } catch {
    // Mất mạng / backend lỗi: giữ trạng thái cũ, mặc định hiển thị.
  }
}

/** Admin bật/tắt một thành phần; báo cho cửa sổ cha / iframe để đồng bộ ngay. */
export async function setUiVisibility(key: string, visible: boolean): Promise<void> {
  const response = await fetchWithAuth(`/ui-visibility/${encodeURIComponent(key)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ visible }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.message || 'Không lưu được. Tài khoản cần quyền quản trị hệ thống.');
  setHidden(payload.data.hidden);
  const message = { type: UI_CHANGED_MESSAGE };
  if (window.parent !== window) window.parent.postMessage(message, window.location.origin);
  document.querySelectorAll('iframe').forEach((frame) => frame.contentWindow?.postMessage(message, window.location.origin));
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function useUiHidden(key: string): boolean {
  return useSyncExternalStore(subscribe, () => hidden.has(key));
}

export function useUiVersion(): number {
  return useSyncExternalStore(subscribe, () => version);
}

export function isUiHidden(key: string): boolean {
  return hidden.has(key);
}

// Chế độ sửa: chỉ trong iframe của /staff/ui-editor (URL có ?ui-edit=1, nhớ qua các lần chuyển trang trong iframe).
const inFrame = typeof window !== 'undefined' && window.self !== window.top;
// Chỉ khi khung cha cùng domain (trang /staff/ui-editor). Site khác nhúng trang này: đọc location của khung cha
// sẽ ném lỗi → không bật chế độ sửa (chống clickjacking công tắc ẩn/hiện).
function parentIsSameOrigin(): boolean {
  try {
    return window.parent.location.origin === window.location.origin;
  } catch {
    return false;
  }
}
function detectEditMode(): boolean {
  if (!inFrame || !parentIsSameOrigin()) return false;
  const params = new URLSearchParams(window.location.search);
  try {
    if (params.has('ui-edit')) {
      sessionStorage.setItem(EDIT_KEY, '1');
      const role = params.get('ui-role');
      if (role === 'guest' || role === 'patient') sessionStorage.setItem(ROLE_KEY, role);
    }
    return sessionStorage.getItem(EDIT_KEY) === '1';
  } catch {
    return params.has('ui-edit');
  }
}
export const UI_EDIT_MODE = detectEditMode();

/** Trong chế độ sửa, xem giao diện như khách hoặc bệnh nhân (admin đăng nhập bằng tài khoản nhân viên). */
export function uiPreviewRole(): 'guest' | 'patient' | null {
  if (!UI_EDIT_MODE) return null;
  try {
    return sessionStorage.getItem(ROLE_KEY) === 'patient' ? 'patient' : 'guest';
  } catch {
    return 'guest';
  }
}

if (typeof window !== 'undefined') {
  void refreshUiVisibility();
  window.addEventListener('message', (event) => {
    if (event.origin === window.location.origin && event.data?.type === UI_CHANGED_MESSAGE) void refreshUiVisibility();
  });
  let lastFocusRefresh = Date.now();
  window.addEventListener('focus', () => {
    if (Date.now() - lastFocusRefresh < 30_000) return;
    lastFocusRefresh = Date.now();
    void refreshUiVisibility();
  });
}
