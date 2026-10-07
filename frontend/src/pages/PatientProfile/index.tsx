import { TypewriterLoader } from '../../components/TypewriterLoader';
import { useEffect, useState, type FormEvent } from 'react';

import { Link } from 'react-router-dom';

import { useDispatch } from 'react-redux';

import { Pencil, X } from 'lucide-react';

import type { AppDispatch } from '../../app/store';

import { initializeAuth } from '../../features/auth/authSlice';

import { readPublishedSession } from '../../features/auth/session';

import { peekCurrentUser, type PatientProfile, type PatientDetails, type PatientProfileUpdate } from '../../features/patient/api';

import { fetchPatientProfile, updateCurrentUser } from './api';

import { Header } from './Header';

import { PortraitUploader } from './PortraitUploader';

import { MedicalTabs } from './MedicalTabs';
import { MedicalHistory } from './MedicalHistory';
import { FamilyProfilesSection } from './FamilyProfilesSection';
import { formatDateVN, birthDateError, vietnamToday } from '../../features/appointment-booking/dateValidation';
import { DateInputVN } from '../../components/DateInputVN';
import type { MedicalTabKey } from './types';



type EditableDetailKey = Exclude<keyof PatientDetails, 'medical_history'>;

type Field = { key: keyof PatientProfile | EditableDetailKey; label: string; details?: boolean; type?: 'date' | 'number' | 'tel' | 'text'; unit?: string; options?: { value: string; label: string }[]; min?: number; max?: number; maxLength?: number };

const coreFields: Field[] = [

  { key: 'full_name', label: 'Họ và tên', maxLength: 200 },

  { key: 'phone', label: 'Số điện thoại liên hệ', type: 'tel', maxLength: 32 },

  { key: 'date_of_birth', label: 'Ngày sinh', type: 'date' },

  { key: 'gender', label: 'Giới tính', options: [{value:'male',label:'Nam'}, {value:'female',label:'Nữ'}, {value:'other',label:'Khác'}, {value:'unspecified',label:'Không muốn cung cấp'}] },

  { key: 'citizen_id', label: 'CCCD / Mã định danh', maxLength: 12 },

  { key: 'health_insurance_code', label: 'Mã thẻ BHYT', maxLength: 32 },

  { key: 'address', label: 'Địa chỉ liên hệ', details: true, maxLength: 500 },

];

const healthFields: Field[] = [

  { key:'blood_type',label:'Nhóm máu',details:true, options:['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(value => ({value,label:value})) },

  { key:'allergies',label:'Thông tin dị ứng',details:true,maxLength:2000 },

  { key:'current_medications',label:'Thuốc đang sử dụng',details:true,maxLength:2000 },

];

const vitalFields: Field[] = [

  {key:'height_cm',label:'Chiều cao',details:true,type:'number',unit:'cm',min:0.1,max:300},

  {key:'weight_kg',label:'Cân nặng',details:true,type:'number',unit:'kg',min:0.1,max:500},

];

const contactFields: Field[] = [

  {key:'emergency_name',label:'Họ tên người liên hệ khẩn cấp',details:true,maxLength:200},

  {key:'emergency_relationship',label:'Mối quan hệ',details:true,maxLength:100},

  {key:'emergency_phone',label:'SĐT người liên hệ khẩn cấp',details:true,type:'tel',maxLength:32},

];

const tabs = [

  {key:'history' as const,label:'Lịch sử khám & Chẩn đoán'},

  {key:'prescriptions' as const,label:'Đơn thuốc'},

  {key:'tests' as const,label:'Xét nghiệm & CĐHA'},

  {key:'timeline' as const,label:'Lịch tiêm chủng'},

];

const emptyMessages: Record<MedicalTabKey, string> = {

  history:'Chưa có dữ liệu lịch sử khám và chẩn đoán.', prescriptions:'Chưa có dữ liệu đơn thuốc.',

  tests:'Chưa có dữ liệu xét nghiệm hoặc chẩn đoán hình ảnh.', timeline:'Chưa có dữ liệu tiêm chủng.',

};

function valueOf(profile: PatientProfile, field: Field): string | number | null | undefined {

  return field.details ? profile.patient_details?.[field.key as EditableDetailKey] : profile[field.key as keyof PatientProfile] as string | null;

}

function displayValue(profile: PatientProfile, field: Field): string {

  const value = valueOf(profile, field);

  if (value == null || value === '') return 'Chưa cung cấp';

  if (field.options) return field.options.find(option => option.value === value)?.label || 'Chưa cung cấp';

  if (field.type === 'date') return formatDateVN(String(value), 'Chưa cung cấp');

  return `${value}${field.unit ? ` ${field.unit}` : ''}`;

}



export default function PatientProfilePage() {

  const [profile, setProfile] = useState<PatientProfile | null>(() => peekCurrentUser() ?? null);

  const [loading, setLoading] = useState(() => !peekCurrentUser());

  const [error, setError] = useState('');

  const [notice, setNotice] = useState('');

  const [activeTab, setActiveTab] = useState<MedicalTabKey>('history');

  const [editing, setEditing] = useState<Field | null>(null);

  const [draft, setDraft] = useState('');

  const [saving, setSaving] = useState(false);

  const [saveError, setSaveError] = useState('');

  const dispatch = useDispatch<AppDispatch>();

  const authenticated = Boolean(readPublishedSession());

  useEffect(() => {

    let active = true;

    if (!authenticated) { setLoading(false); return; }

    fetchPatientProfile().then(data => { if (active) setProfile(data); }).catch((e: unknown) => {

      if (active) setError(e instanceof TypeError ? 'Không thể kết nối máy chủ để tải hồ sơ.' : e instanceof Error ? e.message : 'Không thể tải hồ sơ.');

    }).finally(() => { if (active) setLoading(false); });

    return () => { active = false; };

  }, [authenticated]);

  useEffect(() => {

    if (!editing) return;

    const close = (event: KeyboardEvent) => { if (event.key === 'Escape' && !saving) setEditing(null); };

    window.addEventListener('keydown', close);

    return () => window.removeEventListener('keydown', close);

  }, [editing, saving]);

  function openEditor(field: Field) {

    if (!profile) return;

    setDraft(String(valueOf(profile, field) ?? '')); setEditing(field); setSaveError(''); setNotice('');

  }

  async function save(event: FormEvent) {

    event.preventDefault();

    if (!editing) return;

    let value: string | number | null = draft.trim() || null;

    if (value !== null && editing.type === 'number') value = Number(value);

    if (typeof value === 'string' && editing.type === 'tel') value = value.replace(/[\s.-]/g, '');

    if (value !== null && editing.type === 'tel' && !/^(0|\+84)[35789]\d{8}$/.test(String(value))) { setSaveError('Vui lòng nhập số điện thoại Việt Nam hợp lệ.'); return; }

    if (value !== null && editing.key === 'citizen_id' && !/^\d{12}$/.test(String(value))) { setSaveError('CCCD cần đủ 12 chữ số.'); return; }

    if (value !== null && (editing.type === 'date' || editing.key === 'date_of_birth')) {
      const err = birthDateError(String(value));
      if (err) { setSaveError(err); return; }
    }

    const update: PatientProfileUpdate = editing.details ? { patient_details: { [editing.key]: value } } : { [editing.key]: value };

    setSaving(true); setSaveError('');

    try {

      const updated = await updateCurrentUser(update);

      setProfile(updated); setEditing(null); setNotice(`Đã lưu ${editing.label.toLowerCase()}.`);

      if (editing.key === 'full_name' || editing.key === 'phone') await dispatch(initializeAuth());

    } catch (e) { setSaveError(e instanceof TypeError ? 'Không thể kết nối máy chủ. Thông tin chưa được lưu.' : e instanceof Error ? e.message : 'Không thể lưu thông tin.'); }

    finally { setSaving(false); }

  }

  function section(title: string, fields: Field[], description?: string) {

    return <section className="rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-5 shadow-sm">

      <h2 className="text-base font-semibold text-slate-900 dark:text-app-text light:text-app-text">{title}</h2>

      {description && <p className="mt-1 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">{description}</p>}

      <dl className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">

        {profile && fields.map(field => <div key={field.key}>

          <dt className="text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">{field.label}</dt>

          <dd className="mt-1 flex items-start gap-2">

            <span className={`min-w-0 whitespace-pre-wrap break-words text-sm ${valueOf(profile,field) == null || valueOf(profile,field) === '' ? 'text-slate-400 dark:text-app-secondary light:text-app-secondary' : 'font-medium text-slate-800 dark:text-app-text light:text-app-text'}`}>{displayValue(profile,field)}</span>

            <button type="button" onClick={() => openEditor(field)} aria-label={`Chỉnh sửa ${field.label.toLowerCase()}`} title={`Chỉnh sửa ${field.label.toLowerCase()}`} className="shrink-0 rounded p-1 text-slate-400 dark:text-app-secondary light:text-app-secondary hover:bg-blue-50 dark:hover:bg-blue-950/50 light:hover:bg-app-muted hover:text-blue-600 dark:hover:text-blue-300 light:hover:text-app-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"><Pencil className="h-3.5 w-3.5" /></button>

          </dd>

        </div>)}

      </dl>

    </section>;

  }

  return <div className="patient-theme flex min-h-screen flex-col bg-[#f8fafb] dark:bg-app-page light:bg-app-page">

    <Header />

    <main className="mx-auto w-full max-w-7xl flex-1 space-y-5 px-4 py-6 sm:px-6">

      {loading ? <div className="flex justify-center gap-2 py-20 text-slate-500 dark:text-app-secondary light:text-app-secondary"><TypewriterLoader />Đang tải hồ sơ…</div>

      : !authenticated ? <div className="rounded-2xl border bg-white dark:bg-app-surface light:bg-app-surface p-8 text-center"><p>Vui lòng đăng nhập để xem và chỉnh sửa hồ sơ của bạn.</p><Link to="/login?returnTo=%2Fpatient%2Fprofile" className="mt-4 inline-block rounded-lg bg-blue-600 dark:bg-blue-700 light:bg-app-primary px-5 py-2 text-white">Đăng nhập</Link></div>

      : !profile ? <p role="alert" className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 p-5 text-red-700 dark:text-red-300">{error || 'Không tìm thấy hồ sơ.'}</p>

      : <>

        {error && <p role="alert" className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/50 p-4 text-sm text-amber-900 dark:text-amber-300">Đang hiển thị hồ sơ đã tải trước đó. {error}</p>}

        <div className="flex items-center gap-4 rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-5 shadow-sm">

          <PortraitUploader userId={profile.id} name={profile.full_name || 'Bệnh nhân'} />

          <div className="min-w-0"><h1 className="flex items-center gap-2 text-xl font-bold text-slate-900 dark:text-app-text light:text-app-text">{profile.full_name || 'Chưa cung cấp họ tên'}<button type="button" title="Chỉnh sửa họ tên" aria-label="Chỉnh sửa họ tên" onClick={() => openEditor(coreFields[0])} className="rounded p-1 text-slate-400 dark:text-app-secondary light:text-app-secondary hover:text-blue-600 dark:hover:text-blue-300 light:hover:text-app-primary"><Pencil className="h-4 w-4" /></button></h1><p className="mt-1 break-all text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">{profile.email || 'Chưa có email'}</p><p className="mt-1 break-all text-xs text-slate-400 dark:text-app-secondary light:text-app-secondary">Mã hồ sơ: {profile.id}</p></div>

        </div>

        {notice && <p role="status" className="rounded-xl bg-green-50 dark:bg-green-950/50 p-3 text-sm text-green-700 dark:text-green-300">{notice}</p>}

        {section('Thông tin cá nhân',coreFields)}

        <FamilyProfilesSection />

        {section('Thông tin sức khỏe',healthFields,'Thông tin do bạn cung cấp.')}

        <MedicalHistory history={profile.patient_details?.medical_history || []} onSave={async medical_history => {

          const updated = await updateCurrentUser({ patient_details: { medical_history } });

          setProfile(updated); setNotice('Đã lưu tiền sử bệnh.');

        }} />

        {section('Chỉ số sức khỏe',vitalFields,'Số đo do bạn tự nhập; chưa được nhân viên y tế xác minh.')}

        {profile.patient_details?.height_cm && profile.patient_details?.weight_kg ? <p className="px-2 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">BMI tính từ chiều cao và cân nặng: {(profile.patient_details.weight_kg / (profile.patient_details.height_cm / 100) ** 2).toFixed(1)} kg/m²</p> : null}

        <MedicalTabs tabs={tabs} activeTab={activeTab} onTabChange={key => setActiveTab(key as MedicalTabKey)} />

        <section className="rounded-2xl border border-slate-200 dark:border-app-border light:border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-8 text-center text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">{emptyMessages[activeTab]}</section>

        {section('Liên hệ khẩn cấp',contactFields)}

      </>}

    </main>

    {editing && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 p-4" onClick={event => { if (event.target === event.currentTarget && !saving) setEditing(null); }}>

      <form onSubmit={save} role="dialog" aria-modal="true" aria-labelledby="profile-editor-title" className="w-full max-w-md rounded-2xl bg-white dark:bg-app-surface light:bg-app-surface p-6 shadow-xl">

        <div className="mb-5 flex items-center justify-between"><h2 id="profile-editor-title" className="font-semibold text-slate-900 dark:text-app-text light:text-app-text">Chỉnh sửa {editing.label.toLowerCase()}</h2><button disabled={saving} type="button" aria-label="Đóng chỉnh sửa" onClick={() => setEditing(null)} className="rounded p-1 text-slate-400 dark:text-app-secondary light:text-app-secondary hover:text-slate-700 dark:hover:text-app-text light:hover:text-app-text"><X className="h-5 w-5" /></button></div>

        <label htmlFor="profile-field" className="mb-2 block text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">
          {editing.label}{editing.unit ? ` (${editing.unit})` : ''}{editing.type === 'date' && draft ? ` (dd/mm/yyyy: ${formatDateVN(draft)})` : ''}
        </label>

        {editing.options ? (
          <select autoFocus id="profile-field" value={draft} onChange={e => setDraft(e.target.value)} disabled={saving} className="w-full rounded-lg border border-slate-300 dark:border-app-border light:border-app-border p-3"><option value="">Chưa cung cấp</option>{editing.options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
        ) : editing.type === 'date' ? (
          <DateInputVN
            id="profile-field"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            disabled={saving}
            max={vietnamToday()}
            placeholder="dd/mm/yyyy"
            className="w-full rounded-lg border border-slate-300 dark:border-app-border light:border-app-border p-3 bg-white dark:bg-slate-900"
          />
        ) : (
          <input autoFocus id="profile-field" type={editing.type || 'text'} value={draft} onChange={e => setDraft(e.target.value)} disabled={saving} step={editing.type === 'number' ? ['systolic','diastolic','heart_rate'].includes(editing.key) ? '1' : 'any' : undefined} min={editing.min} max={editing.max} maxLength={editing.maxLength} className="w-full rounded-lg border border-slate-300 dark:border-app-border light:border-app-border p-3" />
        )}

        {saveError && <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-300">{saveError}</p>}

        <div className="mt-5 flex justify-end gap-2"><button type="button" disabled={saving} onClick={() => setEditing(null)} className="rounded-lg border px-4 py-2 text-sm">Hủy</button><button type="submit" disabled={saving} className="rounded-lg bg-blue-600 dark:bg-blue-700 light:bg-app-primary px-4 py-2 text-sm text-white disabled:opacity-50">{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</button></div>

      </form>

    </div>}

  </div>;

}
