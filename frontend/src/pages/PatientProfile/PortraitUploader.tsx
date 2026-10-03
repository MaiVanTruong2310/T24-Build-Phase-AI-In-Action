import { PATIENT_PORTRAIT_UPDATED_EVENT } from '../../components/PatientAvatar';
import { TypewriterLoader } from '../../components/TypewriterLoader';
import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { Camera, UserRound, X } from 'lucide-react';
import { fetchWithAuth } from '../../app/apiClient';
import { cachedQuery, rememberQuery } from '../../app/queryCache';

const MAX_IMAGE_LENGTH = 180000;
const TTL = 5 * 60 * 1000;

async function portraitRequest(image?: string | null, signal?: AbortSignal): Promise<string | null> {
  const response = await fetchWithAuth('/users/me/portrait', image === undefined ? { signal } : {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.detail || 'Không thể lưu ảnh hồ sơ.');
  return payload.data;
}

export function PortraitUploader({ userId, name }: { userId: string; name: string }) {
  const key = `patient-portrait:${userId}`;
  const [portrait, setPortrait] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [position, setPosition] = useState(50);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    setPortrait(null); setSource(null); setError(''); setNotice('');
    cachedQuery(key, TTL, () => portraitRequest()).then(image => { if (active) setPortrait(image); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không thể tải ảnh hồ sơ.'); });
    return () => { active = false; };
  }, [key]);
  useEffect(() => () => { if (source) URL.revokeObjectURL(source); }, [source]);
  useEffect(() => {
    if (!source) return;
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) setSource(null); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [source, busy]);

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setError(''); setNotice('');
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Vui lòng chọn ảnh JPG, PNG hoặc WebP.'); return;
    }
    if (file.size > 10 * 1024 * 1024) { setError('Ảnh cần nhỏ hơn 10 MB.'); return; }
    setPosition(50); setSource(URL.createObjectURL(file));
  }

  async function save(image: string | null) {
    const updated = await portraitRequest(image);
    rememberQuery(key, updated, TTL);
    window.dispatchEvent(new CustomEvent(PATIENT_PORTRAIT_UPDATED_EVENT, { detail: { userId, image: updated } }));
    setPortrait(updated); setSource(null);
    setNotice(image ? 'Đã lưu ảnh hồ sơ 4×6.' : 'Đã gỡ ảnh hồ sơ.');
  }
  async function upload() {
    if (!source) return;
    setBusy(true); setError('');
    try {
      const img = new Image();
      img.src = source;
      await img.decode();
      if (img.naturalWidth * img.naturalHeight > 40_000_000) throw new Error('Ảnh quá lớn. Vui lòng chọn ảnh dưới 40 megapixel.');
      const canvas = document.createElement('canvas');
      canvas.width = 400; canvas.height = 600;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Trình duyệt không thể xử lý ảnh.');
      const scale = Math.max(400 / img.naturalWidth, 600 / img.naturalHeight);
      const width = 400 / scale;
      const height = 600 / scale;
      context.fillStyle = '#ffffff'; context.fillRect(0, 0, 400, 600);
      context.drawImage(img, (img.naturalWidth - width) / 2, (img.naturalHeight - height) * position / 100, width, height, 0, 0, 400, 600);
      let quality = 0.9;
      let image = canvas.toDataURL('image/jpeg', quality);
      while (image.length > MAX_IMAGE_LENGTH && quality > 0.3) {
        quality -= 0.1; image = canvas.toDataURL('image/jpeg', quality);
      }
      if (image.length > MAX_IMAGE_LENGTH) throw new Error('Ảnh có quá nhiều chi tiết. Vui lòng chọn ảnh chân dung khác.');
      await save(image);
    } catch (e) { setError(e instanceof Error ? e.message : 'Không thể lưu ảnh hồ sơ.'); }
    finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setError(''); setNotice('');
    try { await save(null); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không thể gỡ ảnh.'); }
    finally { setBusy(false); }
  }

  return <div className="w-28 shrink-0 text-center">
    <div className="mx-auto flex aspect-[2/3] w-24 items-center justify-center overflow-hidden rounded-lg border border-slate-200 light:border-app-border bg-cyan-50 light:bg-app-muted text-cyan-700 light:text-app-primary">
      {portrait ? <img src={portrait} alt={`Ảnh hồ sơ của ${name}`} className="h-full w-full object-cover" /> : <UserRound className="h-10 w-10" />}
    </div>
    <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" aria-label="Chọn ảnh hồ sơ 4×6" className="hidden" onChange={choose} />
    <button type="button" disabled={busy} onClick={() => inputRef.current?.click()} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-blue-200 light:border-app-border px-2 py-1.5 text-xs font-medium text-blue-700 light:text-app-primary hover:bg-blue-50 light:hover:bg-app-muted disabled:opacity-50"><Camera className="h-3.5 w-3.5" />{portrait ? 'Đổi ảnh' : 'Tải ảnh 4×6'}</button>
    {portrait && <button type="button" disabled={busy} onClick={remove} className="mt-1 block w-full text-xs text-slate-500 light:text-app-secondary hover:text-red-600 disabled:opacity-50">Gỡ ảnh</button>}
    {!source && error && <p role="alert" className="mt-2 break-words text-xs text-red-600">{error}</p>}
    {notice && <p role="status" className="mt-2 text-xs text-emerald-700">{notice}</p>}
    {source && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 p-4 text-left" onClick={event => { if (event.target === event.currentTarget && !busy) setSource(null); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="portrait-editor-title" className="max-h-[90dvh] w-full max-w-sm overflow-y-auto rounded-2xl bg-white light:bg-app-surface p-5 shadow-xl">
        <div className="flex items-center justify-between"><h2 id="portrait-editor-title" className="font-semibold text-slate-900 light:text-app-text">Ảnh hồ sơ 4×6</h2><button autoFocus type="button" disabled={busy} aria-label="Đóng chỉnh sửa ảnh" onClick={() => setSource(null)} className="rounded p-2 text-slate-500 light:text-app-secondary"><X className="h-5 w-5" /></button></div>
        <p className="mt-1 text-xs text-slate-500 light:text-app-secondary">Chọn ảnh chân dung rõ mặt, nhìn thẳng, nền sáng. Ảnh sẽ được cắt theo tỷ lệ 4:6.</p>
        <div className="mx-auto mt-4 aspect-[2/3] w-40 overflow-hidden rounded border bg-white light:bg-app-surface"><img src={source} alt="Xem trước ảnh hồ sơ 4×6" className="h-full w-full object-cover" style={{objectPosition: `50% ${position}%`}} /></div>
        <label className="mt-4 block text-xs text-slate-600 light:text-app-secondary">Căn vị trí ảnh theo chiều dọc<input type="range" min="0" max="100" value={position} disabled={busy} onChange={event => setPosition(Number(event.target.value))} className="mt-2 w-full" /></label>
        {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
        <div className="mt-4 flex justify-end gap-2"><button type="button" disabled={busy} onClick={() => setSource(null)} className="rounded-lg border px-4 py-2 text-sm">Hủy</button><button type="button" disabled={busy} onClick={() => { void upload(); }} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 light:bg-app-primary px-4 py-2 text-sm text-white disabled:opacity-50">{busy && <TypewriterLoader />}{busy ? 'Đang lưu…' : 'Lưu ảnh'}</button></div>
      </div>
    </div>}
  </div>;
}
