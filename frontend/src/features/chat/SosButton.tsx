import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useSelector } from 'react-redux';
import { PhoneCall, ShieldAlert } from 'lucide-react';
import { fetchWithAuth } from '../../app/apiClient';
import type { RootState } from '../../app/store';
import { readGuestProfile } from './profile';
import './SosButton.css';

const COUNTDOWN_SECONDS = 10;
// Bấm tay: chờ vị trí tối đa 3 giây. Hết đếm ngược: vị trí đã xin từ 10 giây trước, chỉ chờ thêm chút để gọi 115 sớm.
const LOCATION_WAIT_MS = 3000;
const FINAL_LOCATION_WAIT_MS = 500;
// Mở trình gọi 115 sau khi request báo bệnh viện đã đi (keepalive giữ request khi trang chuyển sang nền).
const DIAL_DELAY_MS = 700;
const SESSION_KEY = 'p124_chat_session_id';
const PHONE_PATTERN = /^\+?\d{9,12}$/;

type Phase = 'idle' | 'counting' | 'sending' | 'sent' | 'error';

interface Position {
  latitude: number;
  longitude: number;
  accuracy_m: number;
}

interface LocationResult {
  position?: Position;
  error?: string;
}

interface SosButtonProps {
  /** pill: nút tròn đỏ có icon; link: chữ "115" nhỏ trong dòng nhắc cuối khung chat. */
  variant?: 'pill' | 'link';
  /** Giao diện riêng (header, trang chủ): có children thì bỏ qua variant, dùng className + children. */
  className?: string;
  children?: ReactNode;
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

function requestPosition(): Promise<LocationResult> {
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

function normalizePhone(value: string): string {
  return value.replace(/[\s.()-]/g, '');
}

// tel: chỉ quay số được trên điện thoại; trên máy tính phải nhắc người dùng tự gọi.
function canDialFromThisDevice(): boolean {
  try {
    return window.matchMedia('(pointer: coarse)').matches;
  } catch {
    return true;
  }
}

/**
 * Nút cấp cứu 115: bấm → đếm ngược 10 giây (HỦY nếu bấm nhầm) → gửi vị trí, tên, SĐT cho điều phối viên
 * bệnh viện và mở trình gọi 115. Trình duyệt có thể chặn tự mở tel: khi không có thao tác chạm
 * (Chrome Android) hoặc hỏi xác nhận (iOS), nên luôn hiện nút "Gọi 115" để bấm tay.
 * Không đợi được 10 giây thì bấm "Gửi & gọi 115 ngay".
 */
export function SosButton({ variant = 'pill', className, children }: SosButtonProps) {
  const authUser = useSelector((state: RootState) => state.auth.user);
  const [phase, setPhase] = useState<Phase>('idle');
  const [remaining, setRemaining] = useState(COUNTDOWN_SECONDS);
  const [hasLocation, setHasLocation] = useState<boolean | null>(null);
  const [errorText, setErrorText] = useState('');
  const [phoneDraft, setPhoneDraft] = useState('');
  const [canDial] = useState(canDialFromThisDevice);
  // Đếm ngược giữ bản send() lúc mở hộp thoại: đọc SĐT qua ref để lấy giá trị người dùng gõ sau đó.
  const phoneRef = useRef('');
  phoneRef.current = phoneDraft;
  const locationRef = useRef<Promise<LocationResult> | null>(null);
  const timerRef = useRef<number | null>(null);
  const dialTimerRef = useRef<number | null>(null);
  const sentRef = useRef(false);
  // Mỗi lần mở/đóng hộp thoại tăng runRef: kết quả gửi muộn của lần trước không được mở lại hộp thoại.
  const runRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (dialTimerRef.current !== null) {
      window.clearTimeout(dialTimerRef.current);
      dialTimerRef.current = null;
    }
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const patientInfo = useCallback(() => {
    if (authUser) {
      return { name: authUser.full_name || '', phone: authUser.phone || '' };
    }
    const guest = readGuestProfile();
    return { name: guest?.name || '', phone: guest?.phone || '' };
  }, [authUser]);

  const location = useCallback((waitMs: number): Promise<LocationResult> => {
    // Dùng lại yêu cầu vị trí đã gửi lúc mở hộp thoại, không bật hỏi quyền lần hai.
    locationRef.current ??= requestPosition();
    return Promise.race([
      locationRef.current,
      new Promise<LocationResult>(resolve => window.setTimeout(() => resolve({ error: 'Hết thời gian lấy vị trí' }), waitMs)),
    ]);
  }, []);

  const send = useCallback(async (waitMs: number = LOCATION_WAIT_MS) => {
    if (sentRef.current) return;
    sentRef.current = true;
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    const run = runRef.current;
    setPhase('sending');
    const place = await location(waitMs);
    const { name, phone } = patientInfo();
    const typedPhone = normalizePhone(phoneRef.current);
    try {
      const response = await fetchWithAuth(`/coordination/live/${encodeURIComponent(currentSessionId())}/sos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Trình gọi 115 mở ra ngay sau đó đẩy trang xuống nền; keepalive để request không bị hủy.
        keepalive: true,
        body: JSON.stringify({
          latitude: place.position?.latitude ?? null,
          longitude: place.position?.longitude ?? null,
          accuracy_m: place.position?.accuracy_m ?? null,
          location_error: place.position ? null : place.error ?? null,
          patient_name: name || null,
          patient_phone: phone || (PHONE_PATTERN.test(typedPhone) ? typedPhone : null),
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || data.detail || 'Không gửi được cảnh báo.');
      }
      if (run !== runRef.current) return;
      setHasLocation(Boolean(place.position));
      setPhase('sent');
    } catch (error) {
      if (run !== runRef.current) return;
      sentRef.current = false;
      setErrorText(error instanceof Error ? error.message : 'Không gửi được cảnh báo.');
      setPhase('error');
    }
  }, [location, patientInfo]);

  // Hết đếm ngược: báo bệnh viện rồi thử mở trình gọi 115 (không có thao tác chạm nên có thể bị chặn).
  const sendAndDial = useCallback(() => {
    void send(FINAL_LOCATION_WAIT_MS);
    if (!canDial) return;
    const run = runRef.current;
    dialTimerRef.current = window.setTimeout(() => {
      dialTimerRef.current = null;
      if (run === runRef.current) window.location.href = 'tel:115';
    }, DIAL_DELAY_MS);
  }, [canDial, send]);

  const start = useCallback(() => {
    clearTimers();
    runRef.current += 1;
    sentRef.current = false;
    // Xin vị trí ngay khi mở để người dùng kịp bấm "Cho phép" trước khi hết 10 giây.
    locationRef.current = requestPosition();
    setHasLocation(null);
    setErrorText('');
    setRemaining(COUNTDOWN_SECONDS);
    setPhase('counting');
    const deadline = Date.now() + COUNTDOWN_SECONDS * 1000;
    timerRef.current = window.setInterval(() => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left <= 0) sendAndDial();
    }, 200);
  }, [clearTimers, sendAndDial]);

  const close = useCallback(() => {
    clearTimers();
    runRef.current += 1;
    sentRef.current = false;
    setPhase('idle');
  }, [clearTimers]);

  // Bấm tay vào tel:115 (có thao tác chạm nên trình duyệt cho gọi): báo bệnh viện ngay nếu chưa báo.
  const onCallClick = useCallback(() => {
    if (phase === 'counting' || phase === 'error') void send();
  }, [phase, send]);

  const retry = useCallback(() => {
    setErrorText('');
    void send();
  }, [send]);

  useEffect(() => {
    if (phase === 'idle' || phase === 'sending') return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [phase, close]);

  const open = phase !== 'idle';
  const info = patientInfo();
  const needsPhone = !info.phone;

  const trigger = children ? (
    <button type="button" onClick={start} className={`${className ?? ''} cursor-pointer`} aria-label="Cấp cứu 115: sau 10 giây gửi vị trí cho bệnh viện và gọi 115">
      {children}
    </button>
  ) : variant === 'pill' ? (
      <button
        type="button"
        onClick={start}
        className="sos-pill"
        aria-label="Cấp cứu 115: sau 10 giây gửi vị trí cho bệnh viện và gọi 115"
      >
        <PhoneCall size={15} aria-hidden="true" />
        Cấp cứu 115
      </button>
    ) : (
      <button
        type="button"
        onClick={start}
        className="sos-link"
        aria-label="Cấp cứu 115: sau 10 giây gửi vị trí cho bệnh viện và gọi 115"
      >
        115
      </button>
    );

  const deskNote = !canDial && (
    <p className="sos-note">Máy tính không gọi được: hãy dùng điện thoại bấm số 115.</p>
  );

  return (
    <>
      {trigger}
      {open &&
        createPortal(
          <div className="sos-backdrop" role="alertdialog" aria-modal="true" aria-labelledby="sos-title" aria-describedby="sos-desc">
            <div className="sos-card">
              <span className="sos-icon"><ShieldAlert size={30} aria-hidden="true" /></span>
              <h2 id="sos-title" className="sos-title">
                {phase === 'counting' ? 'Gửi cảnh báo cấp cứu' : 'Cấp cứu 115'}
              </h2>

              {phase === 'counting' && (
                <>
                  <p id="sos-desc" className="sos-desc">
                    Sau {COUNTDOWN_SECONDS} giây sẽ gửi vị trí và số điện thoại của bạn cho bệnh viện, đồng thời gọi 115.
                  </p>
                  <div className="sos-count" aria-live="assertive">
                    <span>{remaining}</span>
                  </div>
                  <div className="sos-bar">
                    <div className="sos-bar__fill" style={{ width: `${(remaining / COUNTDOWN_SECONDS) * 100}%` }} />
                  </div>
                  <p className="sos-who">
                    {info.name || 'Chưa có tên'} · {info.phone || 'Chưa có SĐT'}
                  </p>
                  {needsPhone && (
                    <label className="sos-field">
                      SĐT để bệnh viện gọi lại (nếu có)
                      <input
                        type="tel"
                        inputMode="tel"
                        autoComplete="tel"
                        value={phoneDraft}
                        onChange={event => setPhoneDraft(event.target.value)}
                        placeholder="VD: 0912345678"
                        className="sos-input"
                      />
                    </label>
                  )}
                  <div className="sos-actions">
                    <button type="button" autoFocus onClick={close} className="sos-btn sos-btn--ghost">
                      HỦY
                    </button>
                    <a href="tel:115" onClick={onCallClick} className="sos-btn sos-btn--danger">
                      Gửi & gọi 115 ngay
                    </a>
                  </div>
                  {deskNote}
                </>
              )}

              {phase !== 'counting' && (
                <>
                  <p id="sos-desc" className="sos-desc sos-desc--status" aria-live="polite">
                    {phase === 'sending' && 'Đang gửi vị trí cho bệnh viện…'}
                    {phase === 'sent' &&
                      `Đã gửi cảnh báo đến bệnh viện; ứng dụng chưa xác nhận nhân viên đã nhận ca. Hãy gọi 115 để được hỗ trợ ngay.${hasLocation ? '' : ' Chưa lấy được vị trí: hãy cho biết địa chỉ khi gọi 115.'}`}
                    {phase === 'error' && `Chưa gửi được cho bệnh viện: ${errorText}`}
                  </p>
                  <p className="sos-hint">Nếu máy chưa tự gọi, bấm nút dưới để gọi 115:</p>
                  <a
                    href="tel:115"
                    onClick={onCallClick}
                    autoFocus
                    className="sos-btn sos-btn--danger sos-btn--big"
                  >
                    <PhoneCall size={22} aria-hidden="true" />
                    Gọi 115
                  </a>
                  {deskNote}
                  <div className="sos-actions sos-actions--end">
                    {phase === 'error' && (
                      <button type="button" onClick={retry} className="sos-btn sos-btn--dark">
                        Gửi lại cho bệnh viện
                      </button>
                    )}
                    {phase !== 'sending' && (
                      <button type="button" onClick={close} className="sos-btn sos-btn--ghost">
                        Đóng
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
