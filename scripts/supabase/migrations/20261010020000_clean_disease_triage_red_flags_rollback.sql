-- Khôi phục red_flags / warning_signs của disease_triage từ bản sao lưu trước khi làm sạch.
update public.disease_triage d set
  red_flags = b.red_flags,
  warning_signs = b.warning_signs,
  updated_at = b.updated_at
from public.disease_triage_backup_20261010 b
where d.id = b.id;
