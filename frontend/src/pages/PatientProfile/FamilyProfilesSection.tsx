import { useState, useEffect, type FormEvent } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { 
  Users, 
  UserPlus, 
  Pencil, 
  Trash2, 
  X, 
  Calendar, 
  Phone, 
  CreditCard, 
  ShieldCheck, 
  AlertCircle,
  CheckCircle2,
  MapPin
} from 'lucide-react';
import type { RootState } from '../../app/store';
import { 
  fetchPatientProfiles, 
  addPatientProfile, 
  editPatientProfile, 
  archivePatientProfile, 
  relationshipNames, 
  type PatientProfile, 
  type RelativeInput 
} from '../../features/patient-profiles/api';
import { 
  vietnamToday, 
  formatDateVN, 
  birthDateError, 
  calculateAge,
  citizenIdError,
  healthInsuranceCodeError,
} from '../../features/appointment-booking/dateValidation';
import { DateInputVN } from '../../components/DateInputVN';

const emptyDraft: RelativeInput = {
  full_name: '',
  date_of_birth: '',
  gender: '',
  relationship: 'child',
  contact_phone: '',
  citizen_id: '',
  health_insurance_code: '',
  address: '',
  consent_to_manage: false,
};

const relationshipBadges: Record<string, string> = {
  child: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  parent: 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
  spouse: 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
  sibling: 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
  grandparent: 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  other: 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
};

function formatBirthDate(dateStr: string | null): string {
  if (!dateStr) return 'Chưa cập nhật';
  const formatted = formatDateVN(dateStr);
  const age = calculateAge(dateStr);
  return `${formatted}${age !== null ? ` (${age > 0 ? `${age} tuổi` : 'dưới 1 tuổi'})` : ''}`;
}

function formatGender(gender: string | null): string {
  switch (gender) {
    case 'male': return 'Nam';
    case 'female': return 'Nữ';
    case 'other': return 'Khác';
    case 'prefer_not_to_say': return 'Không công bố';
    default: return 'Chưa cập nhật';
  }
}

export function FamilyProfilesSection() {
  const user = useSelector((state: RootState) => state.auth.user);
  const [profiles, setProfiles] = useState<PatientProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<RelativeInput>({ ...emptyDraft, contact_phone: user?.phone || '' });
  const [modalError, setModalError] = useState('');

  const loadProfiles = async () => {
    try {
      const items = await fetchPatientProfiles();
      setProfiles(items);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không thể tải danh sách hồ sơ người thân.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'patient') {
      void loadProfiles();
    }
  }, [user?.id, user?.role]);

  useEffect(() => {
    if (window.location.hash === '#family') {
      const el = document.getElementById('family');
      if (el) {
        setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 150);
      }
    }
  }, []);

  const relatives = profiles.filter(p => !p.is_self);

  const openAddModal = () => {
    setEditingId(null);
    setDraft({ ...emptyDraft, contact_phone: user?.phone || '' });
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (p: PatientProfile) => {
    setEditingId(p.id);
    setDraft({
      full_name: p.full_name || '',
      date_of_birth: p.date_of_birth || '',
      gender: p.gender || '',
      relationship: p.relationship || 'other',
      contact_phone: p.contact_phone || user?.phone || '',
      citizen_id: p.citizen_id || '',
      health_insurance_code: p.health_insurance_code || '',
      address: p.address || '',
      consent_to_manage: true,
    });
    setModalError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (busy) return;
    setIsModalOpen(false);
    setEditingId(null);
    setModalError('');
  };

  const handleField = (key: keyof RelativeInput, value: string | boolean) => {
    setDraft(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;

    if (!draft.full_name.trim()) {
      setModalError('Vui lòng nhập họ và tên người thân.');
      return;
    }
    const dobError = birthDateError(draft.date_of_birth);
    if (dobError) {
      setModalError(dobError);
      return;
    }
    if (!draft.gender) {
      setModalError('Vui lòng chọn giới tính.');
      return;
    }
    if (!draft.contact_phone.trim()) {
      setModalError('Vui lòng nhập số điện thoại liên hệ.');
      return;
    }
    if (draft.citizen_id?.trim()) {
      const cccd = draft.citizen_id.trim();
      const err = citizenIdError(cccd);
      if (err) {
        setModalError(err);
        return;
      }
      const isDuplicate = profiles.some(p => p.id !== editingId && p.citizen_id === cccd);
      if (isDuplicate) {
        setModalError('Số CCCD này đã tồn tại trong danh sách hồ sơ người thân.');
        return;
      }
    }
    if (draft.health_insurance_code?.trim()) {
      const bhyt = draft.health_insurance_code.trim();
      const err = healthInsuranceCodeError(bhyt);
      if (err) {
        setModalError(err);
        return;
      }
      const isDuplicate = profiles.some(p => p.id !== editingId && p.health_insurance_code === bhyt);
      if (isDuplicate) {
        setModalError('Số thẻ bảo hiểm y tế này đã tồn tại trong danh sách hồ sơ người thân.');
        return;
      }
    }
    if (!draft.consent_to_manage) {
      setModalError('Vui lòng đồng ý xác nhận quản lý hồ sơ đặt lịch.');
      return;
    }

    setBusy(true);
    setModalError('');

    try {
      const payload: RelativeInput = {
        ...draft,
        full_name: draft.full_name.trim(),
        citizen_id: draft.citizen_id?.trim() || undefined,
        health_insurance_code: draft.health_insurance_code?.trim() || undefined,
        address: draft.address?.trim() || undefined,
      };

      if (editingId) {
        await editPatientProfile(editingId, payload);
        setNotice(`Đã cập nhật hồ sơ người thân: ${payload.full_name}.`);
      } else {
        await addPatientProfile(payload);
        setNotice(`Đã thêm thành công hồ sơ người thân: ${payload.full_name}.`);
      }

      await loadProfiles();
      setIsModalOpen(false);
      setEditingId(null);
      setTimeout(() => setNotice(''), 5000);
    } catch (e) {
      setModalError(e instanceof Error ? e.message : 'Không thể lưu hồ sơ.');
    } finally {
      setBusy(false);
    }
  };

  const handleArchive = async (p: PatientProfile) => {
    if (busy) return;
    const confirmed = window.confirm(
      `Bạn có chắc chắn muốn gỡ hồ sơ của "${p.full_name}" khỏi danh sách người thân? (Lịch hẹn đã đặt trước đó vẫn được lưu giữ an toàn).`
    );
    if (!confirmed) return;

    setBusy(true);
    setError('');
    try {
      await archivePatientProfile(p.id);
      setNotice(`Đã gỡ hồ sơ "${p.full_name}".`);
      await loadProfiles();
      setTimeout(() => setNotice(''), 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không thể gỡ hồ sơ.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="family" className="rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-5 shadow-sm">
      {/* Header Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
              <Users className="h-4 w-4" />
            </div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-app-text light:text-app-text">
              Hồ sơ người thân trong gia đình
            </h2>
            <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
              {relatives.length}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">
            Quản lý hồ sơ y tế người thân (cha mẹ, con cái, vợ/chồng) để đặt lịch khám nhanh chóng và theo dõi điều trị.
          </p>
        </div>

        <button
          type="button"
          onClick={openAddModal}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition active:scale-95 shrink-0"
        >
          <UserPlus className="h-4 w-4" />
          <span>Thêm người thân</span>
        </button>
      </div>

      {/* Global Alerts */}
      {notice && (
        <div className="mt-4 flex items-center gap-2 rounded-xl bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-800 p-3 text-xs text-green-800 dark:text-green-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{notice}</span>
        </div>
      )}
      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 p-3 text-xs text-red-800 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Relative Profiles List */}
      <div className="mt-5">
        {loading ? (
          <div className="py-8 text-center text-xs text-slate-400 dark:text-app-secondary">
            Đang tải danh sách hồ sơ người thân…
          </div>
        ) : relatives.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-8 text-center bg-slate-50/50 dark:bg-slate-900/30">
            <Users className="mx-auto h-9 w-9 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-300">
              Chưa có hồ sơ người thân nào được liên kết
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Thêm người thân để dễ dàng chọn bệnh nhân khi đặt lịch khám chuyên khoa hoặc trò chuyện với trợ lý AI.
            </p>
            <button
              type="button"
              onClick={openAddModal}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 px-3.5 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-slate-700 transition"
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>Thêm hồ sơ đầu tiên</span>
            </button>
          </div>
        ) : (
          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {relatives.map(p => {
              const badge = relationshipBadges[p.relationship] || relationshipBadges.other;
              const relName = relationshipNames[p.relationship] || p.relationship;
              return (
                <article
                  key={p.id}
                  className="group relative flex flex-col justify-between rounded-xl border border-slate-200/90 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/40 p-4 transition-all hover:border-blue-300 dark:hover:border-blue-800 hover:shadow-sm"
                >
                  <div>
                    {/* Top title & badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="font-semibold text-slate-900 dark:text-app-text truncate text-sm">
                          {p.full_name}
                        </h3>
                        <p className="text-[11px] text-slate-500 dark:text-app-secondary mt-0.5">
                          {formatGender(p.gender)}
                        </p>
                      </div>
                      <span className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${badge}`}>
                        {relName}
                      </span>
                    </div>

                    {/* Metadata list */}
                    <div className="mt-3 space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                        <span>{formatBirthDate(p.date_of_birth)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                        <span>{p.contact_phone || 'Chưa có SĐT'}</span>
                      </div>
                      {p.citizen_id && (
                        <div className="flex items-center gap-2 text-[11px] text-slate-500">
                          <CreditCard className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span>CCCD: {p.citizen_id}</span>
                        </div>
                      )}
                      {p.health_insurance_code && (
                        <div className="flex items-center gap-2 text-[11px] text-slate-500">
                          <ShieldCheck className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span>BHYT: {p.health_insurance_code}</span>
                        </div>
                      )}
                      {p.address && (
                        <div className="flex items-start gap-2 text-[11px] text-slate-500">
                          <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{p.address}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="mt-4 pt-3 border-t border-slate-200/80 dark:border-slate-800 flex items-center justify-between gap-2">
                    <Link
                      to={`/patient/appointments`}
                      className="text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
                    >
                      <Calendar className="h-3 w-3" />
                      <span>Đặt khám</span>
                    </Link>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditModal(p)}
                        disabled={busy}
                        title="Chỉnh sửa hồ sơ"
                        className="rounded p-1 text-slate-400 hover:bg-slate-200/60 dark:hover:bg-slate-800 hover:text-blue-600 dark:hover:text-blue-400 transition"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleArchive(p)}
                        disabled={busy}
                        title="Gỡ hồ sơ khỏi danh sách"
                        className="rounded p-1 text-slate-400 hover:bg-red-50 dark:hover:bg-red-950/40 hover:text-red-600 dark:hover:text-red-400 transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal Add/Edit Relative Profile */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto"
          onClick={e => { if (e.target === e.currentTarget && !busy) closeModal(); }}
        >
          <div className="relative w-full max-w-lg rounded-2xl bg-white dark:bg-app-surface light:bg-app-surface p-6 shadow-2xl border border-slate-200 dark:border-app-border my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-app-border">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-base font-bold text-slate-900 dark:text-app-text">
                  {editingId ? 'Chỉnh sửa hồ sơ người thân' : 'Thêm hồ sơ người thân'}
                </h3>
              </div>
              <button
                type="button"
                onClick={closeModal}
                disabled={busy}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {modalError && (
              <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 p-3 text-xs text-red-700 dark:text-red-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-4 space-y-3.5 text-xs">
              <div className="grid gap-3 sm:grid-cols-2">
                {/* Họ và tên */}
                <div className="sm:col-span-2">
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Họ và tên người thân <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={120}
                    placeholder="VD: Nguyễn Văn An"
                    value={draft.full_name}
                    onChange={e => handleField('full_name', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>

                {/* Quan hệ */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Quan hệ với bạn <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={draft.relationship}
                    onChange={e => handleField('relationship', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  >
                    {Object.entries(relationshipNames)
                      .filter(([key]) => key !== 'self')
                      .map(([key, name]) => (
                        <option key={key} value={key}>{name}</option>
                      ))}
                  </select>
                </div>

                {/* Giới tính */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Giới tính <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={draft.gender}
                    onChange={e => handleField('gender', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  >
                    <option value="">-- Chọn giới tính --</option>
                    <option value="male">Nam</option>
                    <option value="female">Nữ</option>
                    <option value="other">Khác</option>
                    <option value="prefer_not_to_say">Không công bố</option>
                  </select>
                </div>

                {/* Ngày sinh */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Ngày sinh (dd/mm/yyyy) <span className="text-red-500">*</span>
                  </label>
                  <DateInputVN
                    required
                    max={vietnamToday()}
                    value={draft.date_of_birth}
                    onChange={e => handleField('date_of_birth', e.target.value)}
                    placeholder="dd/mm/yyyy"
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>

                {/* SĐT liên hệ */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Số điện thoại liên hệ <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="tel"
                    required
                    maxLength={20}
                    placeholder="VD: 0912345678"
                    value={draft.contact_phone}
                    onChange={e => handleField('contact_phone', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>

                {/* CCCD */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    CCCD / Định danh (nếu có)
                  </label>
                  <input
                    type="text"
                    maxLength={12}
                    placeholder="12 chữ số"
                    value={draft.citizen_id || ''}
                    onChange={e => handleField('citizen_id', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>

                {/* BHYT */}
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Mã thẻ BHYT (nếu có)
                  </label>
                  <input
                    type="text"
                    maxLength={32}
                    placeholder="Mã thẻ bảo hiểm y tế"
                    value={draft.health_insurance_code || ''}
                    onChange={e => handleField('health_insurance_code', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>

                {/* Địa chỉ */}
                <div className="sm:col-span-2">
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Địa chỉ cư trú
                  </label>
                  <input
                    type="text"
                    maxLength={500}
                    placeholder="Số nhà, đường, phường/xã, quận/huyện, tỉnh/TP"
                    value={draft.address || ''}
                    onChange={e => handleField('address', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-app-border bg-white dark:bg-slate-900 p-2.5 text-xs text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Consent checkbox */}
              <label className="mt-3 flex items-start gap-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 p-3 border border-slate-200/80 dark:border-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  required
                  checked={draft.consent_to_manage}
                  onChange={e => handleField('consent_to_manage', e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">
                  Tôi xác nhận được người khám hoặc người giám hộ hợp pháp ủy quyền tạo và quản lý hồ sơ thông tin y tế để đặt lịch khám bệnh này.
                </span>
              </label>

              {/* Submit Buttons */}
              <div className="mt-5 flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200 dark:border-app-border">
                <button
                  type="button"
                  disabled={busy}
                  onClick={closeModal}
                  className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 px-5 py-2 font-semibold text-white shadow-sm transition disabled:opacity-50"
                >
                  {busy ? 'Đang lưu…' : editingId ? 'Cập nhật hồ sơ' : 'Lưu hồ sơ người thân'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
