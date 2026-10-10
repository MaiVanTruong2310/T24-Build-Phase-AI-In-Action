-- Khôi phục ats_level / urgency_tier / max_booking_days / action_directive từ bản sao lưu.
update public.disease_triage d set
  ats_level = b.ats_level, urgency_tier = b.urgency_tier,
  max_booking_days = b.max_booking_days, action_directive = b.action_directive
from public.disease_triage_backup_20261010 b
where d.id = b.id;
