import { useState, type FormEvent } from 'react';
import { Pencil, Plus, X } from 'lucide-react';
import type { MedicalCondition } from '../../features/patient/api';

interface Props {
  history: MedicalCondition[];
  onSave: (history: MedicalCondition[]) => Promise<void>;
}
export function MedicalHistory({ history, onSave }: Props) {
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [status, setStatus] = useState<MedicalCondition['status']>('in_treatment');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  function edit(condition?: MedicalCondition) {
    setEditingId(condition?.id || null); setName(condition?.name || '');
    setStatus(condition?.status || 'in_treatment'); setError(''); setOpen(true);
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) { setError('Vui lòng nhập tên bệnh.'); return; }
    if (!editingId && history.length >= 100) { setError('Hồ sơ chỉ hỗ trợ tối đa 100 bệnh.'); return; }
    const condition: MedicalCondition = { id: editingId || crypto.randomUUID(), name: name.trim(), status };
    const updated = editingId ? history.map(item => item.id === editingId ? condition : item) : [...history, condition];
    setSaving(true); setError('');
    try { await onSave(updated); setOpen(false); }
    catch (e) { setError(e instanceof TypeError ? 'Không thể kết nối máy chủ. Thông tin chưa được lưu.' : e instanceof Error ? e.message : 'Không thể lưu tiền sử bệnh.'); }
    finally { setSaving(false); }
  }
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center justify-between gap-3">
      <h2 className="text-base font-semibold text-slate-900">Tiền sử bệnh / Bệnh nền</h2>
      <button type="button" onClick={() => edit()} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50"><Plus className="h-4 w-4" />Thêm bệnh</button>
    </div>
    <p className="mt-1 text-xs text-slate-500">Thông tin bệnh và tình trạng điều trị do bạn cung cấp.</p>
    {history.length === 0 ? <p className="mt-4 text-sm text-slate-400">Chưa cung cấp tiền sử bệnh.</p> : <ul className="mt-4 divide-y divide-slate-100">
      {history.map(condition => <li key={condition.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
        <span className="min-w-0 break-words text-sm font-medium text-slate-800">{condition.name}</span>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${condition.status === 'recovered' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>{condition.status === 'recovered' ? 'Khỏi' : 'Đang điều trị'}</span>
          <button type="button" onClick={() => edit(condition)} aria-label={`Chỉnh sửa bệnh ${condition.name}`} title="Chỉnh sửa bệnh và trạng thái" className="rounded p-1 text-slate-400 hover:bg-blue-50 hover:text-blue-600"><Pencil className="h-3.5 w-3.5" /></button>
        </div>
      </li>)}
    </ul>}
    {open && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 p-4" onClick={event => { if (event.target === event.currentTarget && !saving) setOpen(false); }}>
      <form onSubmit={save} role="dialog" aria-modal="true" aria-labelledby="medical-history-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl" onKeyDown={event => { if (event.key === 'Escape' && !saving) setOpen(false); }}>
        <div className="mb-5 flex items-center justify-between"><h3 id="medical-history-title" className="font-semibold text-slate-900">{editingId ? 'Chỉnh sửa tiền sử bệnh' : 'Thêm tiền sử bệnh'}</h3><button type="button" disabled={saving} onClick={() => setOpen(false)} aria-label="Đóng" className="rounded p-1 text-slate-400"><X className="h-5 w-5" /></button></div>
        <label htmlFor="condition-name" className="block text-sm text-slate-600">Tên bệnh</label>
        <input id="condition-name" autoFocus required maxLength={200} value={name} onChange={event => setName(event.target.value)} disabled={saving} className="mt-2 w-full rounded-lg border border-slate-300 p-3" />
        <label htmlFor="condition-status" className="mt-4 block text-sm text-slate-600">Trạng thái</label>
        <select id="condition-status" value={status} onChange={event => setStatus(event.target.value as MedicalCondition['status'])} disabled={saving} className="mt-2 w-full rounded-lg border border-slate-300 p-3"><option value="in_treatment">Đang điều trị</option><option value="recovered">Khỏi</option></select>
        {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
        <div className="mt-5 flex justify-end gap-2"><button type="button" disabled={saving} onClick={() => setOpen(false)} className="rounded-lg border px-4 py-2 text-sm">Hủy</button><button type="submit" disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</button></div>
      </form>
    </div>}
  </section>;
}
