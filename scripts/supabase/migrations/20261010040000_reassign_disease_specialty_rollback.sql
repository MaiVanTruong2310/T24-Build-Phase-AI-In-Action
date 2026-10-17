-- Khôi phục chuyên khoa chính của disease_triage từ bản sao lưu.
update public.disease_triage d set
  primary_specialty_code = b.primary_specialty_code,
  primary_specialty_name = b.primary_specialty_name
from public.disease_triage_backup_20261010 b
where d.id = b.id;
