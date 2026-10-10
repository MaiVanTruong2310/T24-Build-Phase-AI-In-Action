import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useSelector } from 'react-redux';
import { PhoneCall, ShieldAlert } from 'lucide-react';
import { fetchWithAuth } from '../../app/apiClient';
import type { RootState } from '../../app/store';
import { readGuestProfile } from './profile';

const COUNTDOWN_SECONDS = 10;
const SESSION_KEY = 'p124_chat_session_id';

type Phase = 'idle' | 'counting' | 'sending' | 'sent' | 'error';

interface Position {
  latitude: number;
  longitude: number;
  accuracy_m: number;
}

interface SosButtonProps {
  /** pill: nút tròn đỏ có icon; link: chữ "115" nhỏ trong dòng nhắc cuối khung chat. */
  variant?: 'pill' | 'link';
}

function currentSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const created = `web-${crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
    sessionStorage.setItem(SESSION_KEY, created);
    return created;
  } catch {
    return `web-${Date.now()}`;
  }
}

function requestPosition(): Promise<{ position?: Position; error?: string }> {
  return new Promise(resolve => {
    if (!('geolocation' in navigator)) {
      resolve({ error: 'Trình duyệt không hỗ trợ định vị' });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos =>
        resolve({
          position: {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy,
          },
        }),
      err => resolve({ error: err.code === err.PERMISSION_DENIED ? 'Người dùng chưa cho phép định vị' : 'Không lấy được vị trí' }),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 15000 },
    );
  });
}

export function SosButton({ variant = 'pill' }: SosButtonProps) {
  const authUser = useSelector((state: RootState) => state.auth.user);
  const [phase, setPhase] = useState<Phase>('idle');
  const [remaining, setRemaining] = useState(COUNTDOWN_SECONDS);
  const [hasLocation, setHasLocation] = useState<boolean | null>(null);
  const [errorText, setErrorText] = useState('');
  const locationRef = useRef<{ position?: Position; error?: string } | null>(null);
  const timerRef = useRef<number | null>(null);
  const sentRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => clearTimer, [clearTimer]);

  const patientInfo = useCallback(() => {
    if (authUser) {
      return { name: authUser.full_name || '', phone: authUser.phone || '' };
    }
    const guest = readGuestProfile();
    return { name: guest?.name || '', phone: guest?.phone || '' };
  }, [authUser]);

  const send = useCallback(async () => {
    if (sentRef.current) return;
    sentRef.current = true;
    setPhase('sending');
    // Chờ tối đa vài giây nếu vị trí chưa về kịp; không chặn việc gửi.
    const location = locationRef.current ?? (await Promise.race([
      requestPosition(),
      new Promise<{ position?: Position; error?: string }>(resolve => window.setTimeout(() => resolve({ error: 'Hết thời gian lấy vị trí' }), 3000)),
    ]));
    const { name, phone } = patientInfo();
    try {
      const response = await fetchWithAuth(`/coordination/live/${encodeURIComponent(currentSessionId())}/sos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: location.position?.latitude ?? null,
          longitude: location.position?.longitude ?? null,
          accuracy_m: location.position?.accuracy_m ?? null,
          location_error: location.position ? null : location.error ?? null,
          patient_name: name || null,
          patient_phone: phone || null,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || data.detail || 'Không gửi được cảnh báo.');
      }
      setHasLocation(Boolean(location.position));
      setPhase('sent');
    } catch (error) {
      sentRef.current = false;
      setErrorText(error instanceof Error ? error.message : 'Không gửi được cảnh báo.');
      setPhase('error');
    }
  }, [patientInfo]);

  const start = useCallback(() => {
    clearTimer();
    sentRef.current = false;
    locationRef.current = null;
    setHasLocation(null);
    setErrorText('');
    setRemaining(COUNTDOWN_SECONDS);
    setPhase('counting');
    // Xin vị trí ngay khi bắt đầu đếm để người dùng kịp bấm "Cho phép" trước khi hết 10 giây.
    void requestPosition().then(result => {
      locationRef.current = result;
    });
    const deadline = Date.now() + COUNTDOWN_SECONDS * 1000;
    timerRef.current = window.setInterval(() => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left <= 0) {
        clearTimer();
        void send();
      }
    }, 200);
  }, [clearTimer, send]);

  const cancel = useCallback(() => {
    clearTimer();
    sentRef.current = false;
    setPhase('idle');
  }, [clearTimer]);

  const open = phase !== 'idle';
  const info = patientInfo();

  const trigger =
    variant === 'pill' ? (
      <button
        type="button"
        onClick={start}
        className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
        aria-label="Cấp cứu 115: bấm để gửi vị trí cho điều phối viên sau 10 giây"
      >
        <PhoneCall className="h-3.5 w-3.5" />
        Cấp cứu 115
      </button>
    ) : (
      <button
        type="button"
        onClick={start}
        className="font-bold text-red-500 hover:underline dark:text-red-400"
        aria-label="Cấp cứu 115: bấm để gửi vị trí cho điều phối viên sau 10 giây"
      >
        115
      </button>
    );

  return (
    <>
      {trigger}
      {open &&
        createPortal(
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 p-4" role="alertdialog" aria-modal="true" aria-labelledby="sos-title">
            <div className="w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-2xl dark:bg-slate-900">
              <ShieldAlert className="mx-auto h-10 w-10 text-red-600" />
              <h2 id="sos-title" className="mt-2 text-lg font-bold text-slate-900 dark:text-white">
                {phase === 'sent' ? 'Đã báo điều phối viên' : phase === 'error' ? 'Chưa gửi được' : 'Gửi cảnh báo cấp cứu'}
              </h2>

              {phase === 'counting' && (
                <>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                    Họ tên, số điện thoại và vị trí hiện tại của bạn sẽ được gửi cho điều phối viên sau
                  </p>
                  <div className="my-4 text-6xl font-extrabold tabular-nums text-red-600" aria-live="assertive">
                    {remaining}
                  </div>
                  <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-red-100">
                    <div className="h-full bg-red-600 transition-[width] duration-200" style={{ width: `${(remaining / COUNTDOWN_SECONDS) * 100}%` }} />
                  </div>
                  <p className="mb-4 text-[11px] text-slate-500 dark:text-slate-400">
                    {info.name || 'Chưa có tên'} · {info.phone || 'Chưa có SĐT'}
                  </p>
                  <div className="flex gap-2">
                    <button type="button" autoFocus onClick={cancel} className="flex-1 rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white hover:bg-slate-700 dark:bg-white dark:text-slate-900">
                      HỦY
                    </button>
                    <button type="button" onClick={() => { clearTimer(); void send(); }} className="flex-1 rounded-xl bg-red-600 px-4 py-3 text-sm font-bold text-white hover:bg-red-700">
                      Gửi ngay
                    </button>
                  </div>
                </>
              )}

              {phase === 'sending' && <p className="my-6 text-sm text-slate-600 dark:text-slate-300">Đang gửi cho điều phối viên…</p>}

              {phase === 'sent' && (
                <>
                  <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                    Điều phối viên đã nhận cảnh báo và sẽ gọi lại cho bạn.
                    {hasLocation ? '' : ' Không lấy được vị trí, hãy cho điều phối viên biết địa chỉ của bạn.'}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">Nếu nguy kịch, hãy gọi 115 ngay, đừng chờ.</p>
                </>
              )}

              {phase === 'error' && <p className="mt-2 text-sm text-red-700 dark:text-red-300">{errorText}</p>}

              {(phase === 'sent' || phase === 'error') && (
                <div className="mt-4 flex gap-2">
                  <a href="tel:115" className="flex-1 rounded-xl bg-red-600 px-4 py-3 text-sm font-bold text-white hover:bg-red-700">
                    Gọi 115
                  </a>
                  {phase === 'error' && (
                    <button type="button" onClick={start} className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 dark:border-slate-600 dark:text-slate-200">
                      Thử lại
                    </button>
                  )}
                  <button type="button" onClick={cancel} className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 dark:border-slate-600 dark:text-slate-200">
                    Đóng
                  </button>
                </div>
              )}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
