import { Visible } from '../../features/uiVisibility/Visible'
import { TypewriterLoader } from '../../components/TypewriterLoader';
import { useEffect, useState, type FormEvent } from 'react';

import { Link } from 'react-router-dom';

import { useDispatch } from 'react-redux';

import { ClipboardList, Pencil, X } from 'lucide-react';

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
import './PatientProfile.css';



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

  function section(id: string, title: string, fields: Field[], description?: string) {

    return <section id={id} className="pp-card">

      <h2 className="pp-h2">{title}</h2>

      {description && <p className="pp-desc">{description}</p>}

      <dl className="pp-fields">

        {profile && fields.map(field => {

          const empty = valueOf(profile, field) == null || valueOf(profile, field) === '';

          return <div key={field.key} className="pp-field">

            <dt>{field.label}</dt>

            <dd>

              <span className={empty ? 'pp-field__value is-empty' : 'pp-field__value'}>{displayValue(profile, field)}</span>

              <button type="button" onClick={() => openEditor(field)} aria-label={`Chỉnh sửa ${field.label.toLowerCase()}`} title={`Chỉnh sửa ${field.label.toLowerCase()}`} className="pp-edit"><Pencil size={14} aria-hidden="true" /></button>

            </dd>

          </div>;

        })}

      </dl>

    </section>;

  }

  const navItems = [
    { href: '#ca-nhan', label: 'Cá nhân' },
    { href: '#family', label: 'Người thân' },
    { href: '#suc-khoe', label: 'Sức khỏe' },
    { href: '#tien-su', label: 'Tiền sử bệnh' },
    { href: '#ho-so-kham', label: 'Hồ sơ khám' },
    { href: '#khan-cap', label: 'Liên hệ khẩn cấp' },
  ];

  return <div className="patient-theme pp flex min-h-screen flex-col bg-app-page dark:bg-app-page light:bg-app-page">

    <Header />

    <main className="pp-main">

      {loading ? <div role="status" className="pp-state"><TypewriterLoader />Đang tải hồ sơ…</div>

      : !authenticated ? <div className="pp-state pp-state--card"><p>Vui lòng đăng nhập để xem và chỉnh sửa hồ sơ của bạn.</p><Link to="/login?returnTo=%2Fpatient%2Fprofile" className="pp-btn pp-btn--primary">Đăng nhập</Link></div>

      : !profile ? <p role="alert" className="pp-alert pp-alert--error">{error || 'Không tìm thấy hồ sơ.'}</p>

      : <>

        {error && <p role="alert" className="pp-alert pp-alert--warn">Đang hiển thị hồ sơ đã tải trước đó. {error}</p>}

        <header className="pp-hero">

          <PortraitUploader userId={profile.id} name={profile.full_name || 'Bệnh nhân'} />

          <div className="pp-hero__text">

            <p className="pp-kicker">Hồ sơ bệnh án</p>

            <h1 className="pp-name">{profile.full_name || 'Chưa cung cấp họ tên'}<button type="button" title="Chỉnh sửa họ tên" aria-label="Chỉnh sửa họ tên" onClick={() => openEditor(coreFields[0])} className="pp-edit"><Pencil size={16} aria-hidden="true" /></button></h1>

            <p className="pp-email">{profile.email || 'Chưa có email'}</p>

            <p className="pp-id">Mã hồ sơ: {profile.id}</p>

          </div>

          <Link to="/patient/progress" className="pp-btn pp-hero__link"><ClipboardList size={18} aria-hidden="true" />Lịch hẹn & tiến trình điều trị</Link>

        </header>

        <nav className="pp-nav" aria-label="Các mục trong hồ sơ">{navItems.map(item => <a key={item.href} href={item.href} className="pp-chip">{item.label}</a>)}</nav>

        {notice && <p role="status" className="pp-alert pp-alert--ok">{notice}</p>}

        {section('ca-nhan','Thông tin cá nhân',coreFields)}

        <Visible id="profile.family"><FamilyProfilesSection /></Visible>

        {section('suc-khoe','Thông tin sức khỏe',healthFields,'Thông tin do bạn cung cấp.')}

        <div id="tien-su"><MedicalHistory history={profile.patient_details?.medical_history || []} onSave={async medical_history => {

          const updated = await updateCurrentUser({ patient_details: { medical_history } });

          setProfile(updated); setNotice('Đã lưu tiền sử bệnh.');

        }} /></div>

        {section('chi-so','Chỉ số sức khỏe',vitalFields,'Số đo do bạn tự nhập; chưa được nhân viên y tế xác minh.')}

        {profile.patient_details?.height_cm && profile.patient_details?.weight_kg ? <p className="pp-bmi">BMI tính từ chiều cao và cân nặng: <strong>{(profile.patient_details.weight_kg / (profile.patient_details.height_cm / 100) ** 2).toFixed(1)} kg/m²</strong></p> : null}

        <Visible id="profile.records"><section id="ho-so-kham" className="pp-card">

          <h2 className="pp-h2">Hồ sơ khám & điều trị</h2>

          <MedicalTabs tabs={tabs} activeTab={activeTab} onTabChange={key => setActiveTab(key as MedicalTabKey)} />

          <p className="pp-empty">{emptyMessages[activeTab]}</p>

        </section></Visible>

        {section('khan-cap','Liên hệ khẩn cấp',contactFields)}

      </>}

    </main>

    {editing && <div className="pp-modal" onClick={event => { if (event.target === event.currentTarget && !saving) setEditing(null); }}>

      <form onSubmit={save} role="dialog" aria-modal="true" aria-labelledby="profile-editor-title" className="pp-dialog">

        <div className="pp-dialog__head"><h2 id="profile-editor-title" className="pp-h2">Chỉnh sửa {editing.label.toLowerCase()}</h2><button disabled={saving} type="button" aria-label="Đóng chỉnh sửa" onClick={() => setEditing(null)} className="pp-x"><X size={18} aria-hidden="true" /></button></div>

        <label htmlFor="profile-field" className="pp-label">
          {editing.label}{editing.unit ? ` (${editing.unit})` : ''}{editing.type === 'date' && draft ? ` (dd/mm/yyyy: ${formatDateVN(draft)})` : ''}
        </label>

        {editing.options ? (
          <select autoFocus id="profile-field" value={draft} onChange={e => setDraft(e.target.value)} disabled={saving} className="pp-input"><option value="">Chưa cung cấp</option>{editing.options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
        ) : editing.type === 'date' ? (
          <DateInputVN
            id="profile-field"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            disabled={saving}
            max={vietnamToday()}
            placeholder="dd/mm/yyyy"
            className="pp-input"
          />
        ) : (
          <input autoFocus id="profile-field" type={editing.type || 'text'} value={draft} onChange={e => setDraft(e.target.value)} disabled={saving} step={editing.type === 'number' ? ['systolic','diastolic','heart_rate'].includes(editing.key) ? '1' : 'any' : undefined} min={editing.min} max={editing.max} maxLength={editing.maxLength} className="pp-input" />
        )}

        {saveError && <p role="alert" className="pp-alert pp-alert--error">{saveError}</p>}

        <div className="pp-dialog__btns"><button type="button" disabled={saving} onClick={() => setEditing(null)} className="pp-btn">Hủy</button><button type="submit" disabled={saving} className="pp-btn pp-btn--primary">{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</button></div>

      </form>

    </div>}

  </div>;

}
