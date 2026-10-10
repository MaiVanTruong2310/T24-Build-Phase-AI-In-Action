# scripts/

Chạy mọi script từ **gốc repo** (vd. `python scripts/run_backend.py`).

| Nhóm | Script | Mục đích |
|---|---|---|
| Chạy app | `run_backend.py` | Khởi động FastAPI (dùng SelectorEventLoop trên Windows) |
| | `run_heartbeat.py` | Chạy vòng heartbeat tự động |
| Cài đặt | `install.py`, `setup.sh` | Bootstrap môi trường |
| | `setup_hooks.ps1`, `setup_hooks.sh` | Cài hook log AI20K |
| Log AI20K | `_pyrun.*`, `log_*.py`, `submit_log.py` | Hook log tự động — **không sửa/chạy tay** |
| Dữ liệu & RAG | `seed_full_database.py`, `seed_doctors.sql` | Seed DB dev |
| | `build_vector_store.py` | Index JSONL vào ChromaDB |
| | `compile_clinical_wiki.py` | Biên dịch dữ liệu thô thành Clinical Wiki Markdown |
| | `link_doctors_to_facilities.py` | Liên kết bác sĩ ↔ cơ sở (mặc định dry run, `--apply` để ghi) |
| Tài khoản | `deploy_supabase_accounts.py`, `verify_logins.py` | Tạo và kiểm tra tài khoản Supabase |
| | `manage_coordinator.py`, `provision_coordinator.py` | Cấp tài khoản điều phối viên |
| Eval & đo đạc | `build_groundtruth_eval.py`, `eval_info.py` | Ground truth / thông tin eval |
| | `stats_telemetry.py` | Thống kê fallback/clarify từ telemetry (có test dùng) |
| | `load_test_chat.py` | Load test endpoint chat (gọi LLM thật, chỉ chạy trên staging) |
| SQL | `sql/`, `supabase/migrations/`, `supabase/apply_migration.py` | SQL phụ trợ và migration Supabase |

`_archive/`: script dùng một lần đã chạy xong (patch code, check/smoke tay, migration cho DB chưa có Alembic). Giữ lại để tra cứu; các file này tính `ROOT = parents[1]` nên nếu cần chạy lại, sửa thành `parents[2]`.
