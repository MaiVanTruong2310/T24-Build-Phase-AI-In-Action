import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../app/apiClient';
import { cachedQuery, peekQuery } from '../app/queryCache';
import type { SessionUser } from '../features/auth/session';

export const PATIENT_PORTRAIT_UPDATED_EVENT = 'patient:portrait-updated';
type PortraitChange = { userId: string; image: string | null };

export function PatientAvatar({ user }: { user: SessionUser }) {
  const key = `patient-portrait:${user.id}`;
  const [portrait, setPortrait] = useState<{ owner: string; image: string | null }>(() => ({ owner: user.id, image: peekQuery<string | null>(key) ?? null }));
  useEffect(() => {
    let active = true;
    let changed = false;
    setPortrait({ owner: user.id, image: peekQuery<string | null>(key) ?? null });
    const update = (event: Event) => {
      const detail = (event as CustomEvent<PortraitChange>).detail;
      if (detail.userId !== user.id) return;
      changed = true;
      setPortrait({ owner: user.id, image: detail.image });
    };
    window.addEventListener(PATIENT_PORTRAIT_UPDATED_EVENT, update);
    if (user.role === 'patient') {
      void cachedQuery<string | null>(key, 5 * 60 * 1000, async () => {
        const response = await fetchWithAuth('/users/me/portrait');
        if (!response.ok) throw new Error('Không thể tải ảnh hồ sơ.');
        const payload = await response.json();
        return payload.data;
      }).then(image => { if (active && !changed) setPortrait({ owner: user.id, image }); })
        .catch(() => undefined);
    }
    return () => { active = false; window.removeEventListener(PATIENT_PORTRAIT_UPDATED_EVENT, update); };
  }, [key, user.id, user.role]);

  const image = portrait.owner === user.id ? portrait.image : null;
  const initials = (user.full_name || 'BN').trim().split(/\s+/).slice(-2).map(word => word[0]).join('').toUpperCase();
  return image
    ? <img src={image} alt={`Ảnh hồ sơ của ${user.full_name || 'bệnh nhân'}`} className="h-12 w-8 shrink-0 rounded-lg border border-slate-300 light:border-app-border object-cover dark:border-slate-700" />
    : <span aria-label={`Ảnh đại diện của ${user.full_name || 'bệnh nhân'}`} className="flex h-12 w-8 shrink-0 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 text-xs font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">{initials}</span>;
}
