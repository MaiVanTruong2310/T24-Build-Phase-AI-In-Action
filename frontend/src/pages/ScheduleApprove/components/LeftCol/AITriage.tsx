import { Activity, AlertTriangle, Brain, ClipboardList } from 'lucide-react';
import type { StaffBookingAITriage } from '../../../AppointmentApproval/api';

const SYMPTOM_LABELS: Record<string, string> = {
  hard_stool: 'Phân khô, cứng', straining: 'Khó đi ngoài', abdominal_bloating: 'Đầy bụng',
  passing_gas: 'Vẫn trung tiện được', unable_to_pass_gas: 'Không trung tiện được', vomiting: 'Nôn',
  fever: 'Sốt', weight_loss: 'Sụt cân', blood_in_stool: 'Có máu trong phân',
  severe_abdominal_pain: 'Đau bụng nhiều', mild_abdominal_pain: 'Đau bụng nhẹ', diarrhea: 'Tiêu chảy',
  heartburn: 'Ợ nóng', abdominal_pain: 'Đau bụng', constipation: 'Táo bón', headache: 'Đau đầu',
  one_sided_headache: 'Đau nửa đầu', nausea: 'Buồn nôn', photophobia: 'Sợ ánh sáng',
  vision_changes: 'Nhìn mờ hoặc thay đổi thị lực', eye_symptoms: 'Khó chịu ở mắt', dizziness: 'Chóng mặt',
  numbness_weakness: 'Tê hoặc yếu', fatigue: 'Mệt mỏi', sore_throat: 'Đau họng', chest_pain: 'Đau tức ngực',
  shortness_of_breath: 'Khó thở', cough: 'Ho', joint_pain: 'Đau khớp', back_pain: 'Đau lưng',
  neck_shoulder_pain: 'Đau cổ, vai gáy', muscle_pain: 'Đau cơ', hair_loss: 'Rụng tóc', insomnia: 'Khó ngủ',
  skin_lesion: 'Vấn đề về da', urinary_symptoms: 'Bất thường khi tiểu tiện', neck_lump: 'Nổi cục vùng cổ',
  pregnancy_care: 'Nhu cầu chăm sóc thai kỳ', low_mood: 'Tâm trạng buồn',
  gynecologic_symptoms: 'Triệu chứng phụ khoa', ear_nose_symptoms: 'Triệu chứng tai, mũi hoặc họng',
  dental_pain: 'Đau răng', eating_normally: 'Ăn uống bình thường',
};

function symptomLabel(value: unknown): string | null {
  const code = typeof value === 'string' ? value : typeof value === 'object' && value !== null && 'code' in value ? String(value.code) : '';
  if (SYMPTOM_LABELS[code]) return SYMPTOM_LABELS[code];
  if (code.startsWith('mild_') && SYMPTOM_LABELS[code.slice(5)]) return `Đau nhẹ: ${SYMPTOM_LABELS[code.slice(5)]!.toLocaleLowerCase('vi-VN')}`;
  if (code.startsWith('severe_') && SYMPTOM_LABELS[code.slice(7)]) return `Đau nhiều: ${SYMPTOM_LABELS[code.slice(7)]!.toLocaleLowerCase('vi-VN')}`;
  return null;
}

function readableSymptomText(value: string) {
  return symptomLabel(value) || (!value.includes('_') && /\s/.test(value) ? value : null);
}

function symptomCodes(facts: Record<string, unknown>, polarity: 'positive' | 'negative'): unknown[] {
  if (polarity === 'positive' && Array.isArray(facts.active_complaint_codes) && facts.active_complaint_codes.length) return facts.active_complaint_codes;
  if (Array.isArray(facts.complaints)) {
    const matching = facts.complaints.filter(item => typeof item === 'object' && item !== null && (!('status' in item) || item.status === (polarity === 'positive' ? 'active' : 'denied')));
    if (matching.length) return matching;
  }
  const values = facts[polarity === 'positive' ? 'positive_facts' : 'negative_facts'];
  return Array.isArray(values) ? values : [];
}

function readableLocation(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  const location = value.trim();
  const translations: Record<string, string> = {
    'left abdomen': 'bụng bên trái', 'right abdomen': 'bụng bên phải', abdomen: 'bụng',
    head: 'đầu', chest: 'ngực', back: 'lưng', throat: 'họng',
  };
  return translations[location.toLowerCase()] || (/[^a-z0-9\s]/i.test(location) ? location : null);
}

function ClinicalFacts({ facts, fallback }: { facts: Record<string, unknown>; fallback?: string | null }) {
  const positive = [...new Set(symptomCodes(facts, 'positive').map(symptomLabel).filter((item): item is string => Boolean(item)))];
  const negative = [...new Set(symptomCodes(facts, 'negative').map(symptomLabel).filter((item): item is string => Boolean(item)))].filter(item => !positive.includes(item));
  const chief = symptomLabel(facts.chief_complaint);
  if (chief && !positive.includes(chief)) positive.unshift(chief);
  const duration = typeof facts.duration_days === 'number' && facts.duration_days > 0 ? `${facts.duration_days} ngày` : null;
  const location = readableLocation(facts.location);
  const subject = facts.subject === 'self' ? 'Bản thân' : facts.subject === 'other' ? 'Người khác' : null;
  const fallbackText = typeof fallback === 'string' && fallback.trim() && !fallback.trim().startsWith('{') ? fallback.trim() : null;
  if (!positive.length && !negative.length && !duration && !location && !subject && !fallbackText) return null;
  return (
    <section aria-labelledby="clinical-facts-title" className="rounded-xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-white p-4">
      <div className="mb-3 flex items-center gap-2"><span className="rounded-lg bg-teal-100 p-2 text-teal-800"><ClipboardList size={16} /></span><div><h3 id="clinical-facts-title" className="font-semibold text-slate-800">Tóm tắt triệu chứng</h3><p className="text-xs text-slate-500">Thông tin được ghi nhận khi trao đổi</p></div></div>
      <div className="space-y-2 text-sm leading-6 text-slate-700">
        {subject && <p><span className="font-medium text-slate-500">Người được mô tả:</span> {subject}</p>}
        {positive.length > 0 ? <p><span className="font-medium text-slate-500">Đang gặp:</span> {positive.join(', ')}.</p> : fallbackText && <p>{fallbackText}</p>}
        {negative.length > 0 && <p><span className="font-medium text-slate-500">Người bệnh cho biết không có:</span> {negative.join(', ')}.</p>}
        {(duration || location) && <p>{duration && <>Kéo dài khoảng {duration}</>}{duration && location && ' · '}{location && <>Vị trí: {location}</>}.</p>}
      </div>
    </section>
  );
}

function urgencyLabel(value: string) {
  const labels: Record<string, string> = { routine: 'Thông thường', low: 'Thấp', medium: 'Cần lưu ý', high: 'Ưu tiên sớm', urgent: 'Khẩn cấp', emergency: 'Cấp cứu' };
  return labels[value.toLowerCase()] || null;
}

export function AITriage({ triage }: { triage: StaffBookingAITriage | null }) {
  if (!triage || Object.keys(triage).length === 0) {
    return <p className="text-sm text-slate-500">Chưa có thông tin phân loại ca được lưu.</p>;
  }

  const specialties = (triage.candidate_specialties || []).map(item => item.name || item.specialty_name).filter((name): name is string => typeof name === 'string' && Boolean(name));
  const pipeline = triage.care_pipeline;
  const steps = pipeline?.pipeline_steps || [];
  const urgency = triage.urgency_tier ? urgencyLabel(triage.urgency_tier) : null;

  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap gap-2">
        {urgency && <span className="rounded-full bg-amber-50 px-3 py-1 font-semibold text-amber-800">Mức ưu tiên: {urgency}</span>}
        {triage.is_emergency && <span className="rounded-full bg-red-100 px-3 py-1 font-bold text-red-800">Ca cấp cứu</span>}
      </div>
      {triage.emergency_warning && <div role="alert" className="flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800"><AlertTriangle className="h-4 w-4 shrink-0" />{triage.emergency_warning}</div>}
      {triage.clinical_facts && <ClinicalFacts facts={triage.clinical_facts} fallback={triage.symptoms} />}
      {!triage.clinical_facts && triage.symptoms && <p className="rounded-xl bg-teal-50 p-3 text-slate-700"><b>Triệu chứng được mô tả:</b> {triage.symptoms}</p>}
      {triage.suggested_department_name && <p><b>Chuyên khoa phù hợp:</b> {triage.suggested_department_name}</p>}
      {!!specialties.length && <div><b>Các chuyên khoa có thể cân nhắc</b><ul className="mt-1 list-inside list-disc text-slate-700">{[...new Set(specialties)].map(name => <li key={name}>{name}</li>)}</ul></div>}
      {pipeline && !!steps.length && <div><p className="flex items-center gap-2 font-semibold"><Activity className="h-4 w-4" />Các bước khám được đề xuất</p>{steps.map((step, index) => { const readableSymptoms = (step.target_symptoms || []).map(readableSymptomText).filter((value): value is string => Boolean(value)); return <div key={`${step.step_number || index}-${step.department_name}`} className="mt-2 rounded-lg bg-slate-50 p-3"><b>Bước {step.step_number || index + 1}: {step.department_name || 'Chuyên khoa'}</b>{readableSymptoms.length > 0 && <p className="mt-1 text-slate-600">Đánh giá thêm: {readableSymptoms.join(', ')}</p>}{step.clinical_rationale && <p className="mt-1 text-slate-600">Lý do: {step.clinical_rationale}</p>}</div>})}</div>}
      {triage.captured_at && <p className="flex items-center gap-1 text-xs text-slate-500"><Brain className="h-3 w-3" />Ghi nhận lúc {new Date(triage.captured_at).toLocaleString('vi-VN')}</p>}
    </div>
  );
}
