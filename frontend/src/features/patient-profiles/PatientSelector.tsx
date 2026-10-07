import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import type { RootState } from '../../app/store';
import { fetchPatientProfiles, relationshipNames, type PatientProfile } from './api';
import { formatDateVN } from '../appointment-booking/dateValidation';

export function usePatientSelection() {
  const user = useSelector((state: RootState) => state.auth.user);
  const [profileId, setProfileId] = useState('');
  const [profiles, setProfiles] = useState<PatientProfile[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setProfileId('');
    setProfiles([]);
    setError('');
    if (user?.role !== 'patient') return;
    setLoading(true);
    fetchPatientProfiles()
      .then(items => { if (active) setProfiles(items); })
      .catch(e => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user?.id, user?.role]);

  return {
    profileId,
    profiles,
    selectedProfile: profiles.find(p => p.id === profileId),
    loading,
    error,
    choose: setProfileId,
  };
}

export function PatientSelector({
  selection,
  disabled = false,
}: {
  selection: ReturnType<typeof usePatientSelection>;
  disabled?: boolean;
}) {
  const user = useSelector((state: RootState) => state.auth.user);
  if (user?.role !== 'patient') return null;

  const profile = selection.selectedProfile;
  const relatives = selection.profiles.filter(p => !p.is_self);
  const incomplete = !profile && (!user.full_name || !user.phone || !user.date_of_birth || !user.gender);

  return (
    <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 text-slate-900 dark:text-white shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 mb-2">
        <label htmlFor="patient-profile-select" className="block text-sm font-semibold">
          Bạn đang đặt khám / tư vấn cho ai?
        </label>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Quản lý người thân tại <Link className="text-blue-600 dark:text-blue-400 underline font-medium hover:text-blue-700" to="/patient/profile#family">Hồ sơ bệnh án</Link>
        </span>
      </div>

      <select
        id="patient-profile-select"
        className="w-full rounded-xl border border-slate-300 dark:border-slate-700 p-2.5 text-xs sm:text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:border-blue-500"
        value={selection.profileId}
        disabled={disabled || selection.loading}
        onChange={e => selection.choose(e.target.value)}
      >
        <option value="">Bản thân — {user.full_name || 'Tài khoản chính'}</option>
        {relatives.map(p => (
          <option key={p.id} value={p.id}>
            {p.full_name} · {relationshipNames[p.relationship] || p.relationship}
          </option>
        ))}
      </select>

      {profile && (
        <div className="mt-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5 text-xs text-slate-600 dark:text-slate-300 flex flex-wrap gap-x-4 gap-y-1">
          <span><strong>Người khám:</strong> {profile.full_name}</span>
          <span><strong>Ngày sinh:</strong> {formatDateVN(profile.date_of_birth, 'Chưa cập nhật')}</span>
          <span><strong>Liên hệ:</strong> {profile.contact_phone || 'Chưa cập nhật'}</span>
        </div>
      )}

      {incomplete && (
        <p role="alert" className="mt-2.5 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2.5 rounded-lg border border-amber-200 dark:border-amber-800">
          Hồ sơ bản thân còn thiếu thông tin. <Link className="underline font-semibold" to="/patient/profile">Bổ sung thông tin trong Hồ sơ bệnh án</Link> trước khi đặt khám.
        </p>
      )}

      {selection.error && (
        <p role="alert" className="mt-2 text-xs text-red-600">{selection.error}</p>
      )}
    </section>
  );
}
