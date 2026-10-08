import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { ChevronDown, User } from 'lucide-react';
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

import { type PatientSelection } from './usePatientSelection';

export function PatientSelector({
  selection,
  disabled = false,
}: {
  selection: PatientSelection;
  disabled?: boolean;
}) {
  const user = useSelector((state: RootState) => state.auth.user);
  const [isExpanded, setIsExpanded] = useState(false);

  if (user?.role !== 'patient') return null;

  const profile = selection.selectedProfile;
  const relatives = selection.profiles.filter(p => !p.is_self);
  const incomplete = !profile && (!user.full_name || !user.phone || !user.date_of_birth || !user.gender);

  const selectedName = profile
    ? `${profile.full_name} (${relationshipNames[profile.relationship] || profile.relationship})`
    : `Bản thân — ${user.full_name || 'Tài khoản chính'}`;

  return (
    <section className="border-b border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-[#0B1329]/95 text-slate-900 dark:text-white transition-all">
      {/* ─── Thanh thu gọn (Accordion Header) ─── */}
      <button
        type="button"
        onClick={() => setIsExpanded(prev => !prev)}
        aria-expanded={isExpanded}
        aria-label="Thu gọn hoặc mở rộng chọn người khám"
        className="flex w-full items-center justify-between px-3.5 py-2 text-left hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2 min-w-0 pr-2">
          <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-[#176a52] dark:text-emerald-300">
            <User className="h-3 w-3" />
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 shrink-0 font-medium">
            Đang khám cho:
          </span>
          <span className="font-semibold text-slate-800 dark:text-slate-100 text-[11px] truncate">
            {selectedName}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors">
          <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-medium">
            {isExpanded ? 'Thu gọn' : 'Đổi người khám'}
          </span>
          <ChevronDown
            className={`h-4 w-4 text-slate-400 dark:text-slate-500 transition-transform duration-200 ${
              isExpanded ? 'rotate-180 text-emerald-600 dark:text-emerald-400' : ''
            }`}
          />
        </div>
      </button>

      {/* ─── Nội dung sổ xuống (Expanded Panel) ─── */}
      {isExpanded && (
        <div className="border-t border-slate-100 dark:border-slate-800/80 p-3 bg-[#f8faf9] dark:bg-[#080E1F]/60 space-y-2.5 animate-in fade-in-50 duration-150">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <label htmlFor="patient-profile-select" className="block text-xs font-semibold text-slate-800 dark:text-slate-200">
              Bạn đang đặt khám / tư vấn cho ai?
            </label>
            <span className="text-[10px] text-slate-500 dark:text-slate-400">
              Quản lý người thân tại{' '}
              <Link
                className="text-emerald-700 dark:text-cyan-400 underline font-medium hover:text-emerald-800"
                to="/patient/profile#family"
              >
                Hồ sơ bệnh án
              </Link>
            </span>
          </div>

          <select
            id="patient-profile-select"
            className="w-full rounded-xl border border-slate-300 dark:border-slate-700 p-2 text-xs bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20"
            value={selection.profileId}
            disabled={disabled || selection.loading}
            onChange={e => {
              selection.choose(e.target.value);
              // Tự động thu gọn lại sau khi chọn để tiết kiệm diện tích
              setIsExpanded(false);
            }}
          >
            <option value="">Bản thân — {user.full_name || 'Tài khoản chính'}</option>
            {relatives.map(p => (
              <option key={p.id} value={p.id}>
                {p.full_name} · {relationshipNames[p.relationship] || p.relationship}
              </option>
            ))}
          </select>

          {profile && (
            <div className="rounded-lg bg-white dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60 p-2 text-[11px] text-slate-600 dark:text-slate-300 flex flex-wrap gap-x-3 gap-y-0.5">
              <span><strong>Người khám:</strong> {profile.full_name}</span>
              <span><strong>Ngày sinh:</strong> {formatDateVN(profile.date_of_birth, 'Chưa cập nhật')}</span>
              <span><strong>Liên hệ:</strong> {profile.contact_phone || 'Chưa cập nhật'}</span>
            </div>
          )}

          <p className="text-[10px] text-slate-500 dark:text-slate-400 italic">
            Hồ sơ người khám đang chọn · Hội thoại được tách riêng theo người khám.
          </p>

          {incomplete && (
            <p role="alert" className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-lg border border-amber-200 dark:border-amber-800">
              Hồ sơ bản thân còn thiếu thông tin.{' '}
              <Link className="underline font-semibold" to="/patient/profile">
                Bổ sung trong Hồ sơ bệnh án
              </Link>{' '}
              trước khi đặt khám.
            </p>
          )}

          {selection.error && (
            <p role="alert" className="text-xs text-red-600">{selection.error}</p>
          )}
        </div>
      )}
    </section>
  );
}
