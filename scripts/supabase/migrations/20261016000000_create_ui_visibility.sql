-- Bảng ui_visibility: admin bật/tắt hiển thị từng thành phần giao diện người dùng (/staff/ui-editor).
-- Chỉ lưu thành phần đã chỉnh; không có dòng = hiển thị. Bảng mới, không đụng dữ liệu cũ nên không cần sao lưu.
-- Cùng nội dung với alembic/versions/0034_ui_visibility.py (dùng if not exists nên chạy alembic sau cũng an toàn).
-- RLS bật, không policy: chặn truy cập qua PostgREST anon/authenticated; backend truy cập trực tiếp như các bảng khác.
-- Khôi phục: 20261016000000_create_ui_visibility_rollback.sql
begin;
create table if not exists public.ui_visibility (
  key varchar(120) primary key,
  visible boolean not null default true,
  updated_by uuid null references public.users(id) on delete set null,
  updated_at timestamptz not null default now()
);
alter table public.ui_visibility enable row level security;
commit;
