-- Làm sạch disease_triage.red_flags (dữ liệu crawl: câu văn bài báo, không phải danh sách dấu hiệu).
-- Bằng chứng: cụm rác ("ngoài ra", "ví dụ", "tiêu chảy" gắn Nhồi máu cơ tim ATS 1) từng đẩy câu thường lên cấp cứu.
-- Quy tắc cho từng câu trong red_flags:
--   1. Câu dịch tễ / bối cảnh (tỷ lệ, tử vong, thống kê, ví dụ, liên quan đến, nghiên cứu, ...) → bỏ cả câu.
--   2. Tách câu theo [,:;], bỏ phần trong ngoặc, hạ chữ thường:
--      - cụm chứa dấu hiệu nguy kịch (khớp DB_RED_FLAG_CRITICAL_MARKERS trong triage_service.py) → giữ ở red_flags
--      - cụm rác (< 5 ký tự, mở đầu "ngoài ra"/"ví dụ"/số, từ đơn chung chung) → bỏ
--      - còn lại là triệu chứng thường → chuyển sang warning_signs (gộp, bỏ trùng)
-- Sao lưu: public.disease_triage_backup_20261010 (RLS bật, không policy → chỉ service role đọc được).
-- Khôi phục: 20261010020000_clean_disease_triage_red_flags_rollback.sql

create table if not exists public.disease_triage_backup_20261010 as table public.disease_triage;
alter table public.disease_triage_backup_20261010 enable row level security;

with frag as (
  select d.disease_key,
    trim(regexp_replace(lower(f.part), '\(.*?\)', '', 'g')) as f,
    lower(s.sentence) ~ '(tỷ lệ|tử vong|thống kê|chiếm|ví dụ|liên quan đến|nguy cơ mắc|theo (hiệp hội|tổ chức|nghiên cứu)|nghiên cứu|trên (toàn )?thế giới|hàng năm|ca mắc|globocan|khác với)' as ctx
  from public.disease_triage d
  cross join lateral unnest(d.red_flags) s(sentence)
  cross join lateral regexp_split_to_table(s.sentence, '[,:;]+') f(part)
), cls as (
  select disease_key, f, case
    when ctx then 'drop'
    when length(f) < 5 then 'drop'
    when f ~ '^(ngoài ra|ví dụ|ban đầu|lúc này|tuy nhiên|đây là|nhận thức|bệnh viêm|giai đoạn [0-9])'
      or f ~ '^[0-9]'
      or f ~ '^(thần kinh|hô hấp|đau đớn|nhầm lẫn|kích thích|giãn mạch)$' then 'drop'
    when f ~ '(hôn mê|bất tỉnh|mất ý thức|ngừng thở|ngưng thở|ngừng tim|không thở được|tím tái|tím môi|môi tím|vã mồ hôi lạnh|trụy mạch|trụy tim mạch|sốc|tụt huyết áp|ngạt thở|thở rít|suy hô hấp|thiếu oxy|khó đánh thức|gọi khó tỉnh|li bì|lơ mơ|ngủ lịm|vô niệu|phù phổi|bọt hồng|nôn ra máu|ho ra máu|đi ngoài ra máu|xuất huyết não|liệt|méo miệng|nói lấp|co giật|động kinh|đột quỵ)' then 'red_flag'
    else 'warning' end as c
  from frag
), agg as (
  select disease_key,
    array_agg(distinct f) filter (where c = 'red_flag') as red,
    array_agg(distinct f) filter (where c = 'warning') as warn
  from cls group by disease_key
)
update public.disease_triage d set
  red_flags = coalesce(a.red, '{}'),
  warning_signs = (
    select coalesce(array_agg(distinct x), '{}')
    from unnest(coalesce(d.warning_signs, '{}') || coalesce(a.warn, '{}')) as x
  ),
  updated_at = now()
from agg a
where d.disease_key = a.disease_key;
