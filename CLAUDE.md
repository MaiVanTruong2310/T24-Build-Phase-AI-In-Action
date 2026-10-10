# CLAUDE.md — VCare+ (P-124)

## 1. Tổng quan
VCare+ là trợ lý tiếp đón y tế Vinmec (AI20K Cohort 4, mã P-124). Bệnh nhân chat để phân tầng cấp cứu ATS, định tuyến chuyên khoa, tìm bác sĩ/lịch trống và đặt lịch. Điều phối viên can thiệp qua HITL Coordinator Workbench.
Mục tiêu hiện tại: chấm điểm / Demo Day AI20K và nền móng pilot thực tế. Ưu tiên: luồng lâm sàng an toàn, HITL Workbench, Auth Supabase, test + safety benchmark xanh, báo cáo thực nghiệm.
Không phải monorepo: backend Python ở gốc repo, frontend độc lập trong `frontend/`.

## 2. Tech stack
- Backend: Python 3.11 (`.python-version`; pyproject cho phép >=3.11,<3.13), FastAPI, SQLAlchemy async + psycopg3, Alembic, LangGraph/LangChain, ChromaDB + SQLite FTS5 (Hybrid RAG), Presidio (DLP). Package manager: pip + `requirements.txt`.
- DB/Auth: Postgres (pgvector) và Supabase; `AUTH_PROVIDER` chỉ nhận `supabase`.
- Frontend: React 19, TypeScript ~5.8, Vite 7, Tailwind 4, Redux Toolkit, Zod, PWA. Node 20+, npm.
- Hạ tầng: Docker Compose trên EC2 (backend), Vercel (frontend), GitHub Actions self-hosted runner.

## 3. Lệnh thường dùng
```bash
# Backend (chạy ở thư mục gốc)
pip install -r requirements.txt
python scripts/run_backend.py            # nên dùng thay uvicorn trên Windows (cần SelectorEventLoop)
ruff check src/ tests/
ruff format src/ tests/
pytest tests/ -m "not integration"       # bộ chạy trước khi push
pytest tests/test_medical_assistant/test_emergency_safety_v3.py -v   # 1 file
alembic upgrade head

# Frontend (trong frontend/)
npm ci && npm run dev
npm run lint && npm run build
node tests/coordinator-session-chat.cjs && node tests/chat-regression.cjs   # khi đụng chat

# Eval
python eval/run_realistic_benchmark.py
```
(Lệnh lấy từ Makefile/CI/README; chưa chạy thử trong phiên thiết lập.)

## 4. Cấu trúc quan trọng
- `src/medical_assistant/` — **code production của agent**: `agent/` (graph + nodes), `domain/` (triage, guardrail, probing, care pipeline), `rag/`, `ingestion/`, `api/`.
- `src/api/endpoints/`, `services/`, `repositories/`, `models/`, `schemas/` — REST nghiệp vụ (auth, booking, workbench, catalog...). `src/main.py` là entry.
- `alembic/versions/` — migration; `scripts/sql/`, `scripts/supabase/migrations/` — SQL phụ trợ.
- `configs/control_plane/` — chính sách lâm sàng (Clinical Soul, Protocols).
- `frontend/src/{features,pages,layouts,lib}` — UI; `tests/*.cjs` ở gốc và `frontend/tests/` là test Node.
- `docs/agent/` — tài liệu agent chuẩn (có trong git). `eval/` — benchmark.

## 5. Quy ước code và git
- Ruff (`ruff.toml`): line-length 120, indent bằng space, dấu nháy kép, rule `E,F,I,N,W,UP`, bỏ qua `E501`.
- pytest: `asyncio_mode = strict` (test async cần `@pytest.mark.asyncio`); marker `integration` cho test cần LLM/DB thật.
- Log có cấu trúc qua `log_event(logger, level, "domain.action", description=..., ...)` từ `src/core/logging.py`; lỗi nghiệp vụ dùng `AppError` (`src/core/exceptions.py`).
- Test API dùng fixture `client` trong `tests/conftest.py` (đã mock DB session, không mở DB thật).
- Git: nhánh `feature/...` → PR vào `develop` (CI chạy) → ổn định mới merge `main`. **Không push thẳng `main`.**
- Commit bắt buộc Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `ci:`, có thể kèm scope `feat(auth):`); tiếng Việt hoặc Anh đều được.
- "Ponytail": sửa tối thiểu, đúng chỗ; ưu tiên API/thư viện sẵn có; không refactor ngoài yêu cầu, không trừu tượng hoá sớm.
- Database: thao tác schema/dữ liệu qua Supabase MCP (cấu hình bằng `claude mcp add --scope project`, xác thực bằng `/mcp`).

## 6. Lưu ý và bẫy
- `src/agents/` là legacy (chỉ giữ cho `tests/test_agents`); runtime chỉ mount `src.medical_assistant.api.routes`. Đừng thêm code vào đó.
- `context_agent/` là ngữ cảnh local (nằm trong `.gitignore`); bản chuẩn là `docs/agent/`.
- `.env.example` thiếu các biến `OPENROUTER_*`/`GOOGLE_AI_*` mà code/README dùng. LLM chính theo README là OpenRouter, có failover sang Gemini/OpenAI/DeepSeek.
- Vite không cấu hình proxy `/api` (README nói có là sai): frontend gọi thẳng `VITE_API_BASE_URL`, mặc định trỏ backend dev; ghi đè trong `frontend/.env.local`.
- OTP đăng ký đang mock (`123456`) cho demo.
- `DATABASE_AUTO_CREATE=true` tạo bảng ORM khi khởi động, có thể lệch với Alembic; có 2 file migration cùng số `0021`, head được merge ở `0023`.
- Nhiều tài liệu ghi `ci.yml`, file thật là `.github/workflows/ci_cd.yml`. `CODEOWNERS`/`CONTRIBUTING.md` là của template AI20K.
- CORS/cookie: cookie `SameSite=none; Secure` cần HTTPS và `CORS_ORIGINS` khớp chính xác.
- Log AI tự động (hook + pre-push). Nếu pre-push lỗi: báo lại, không `--no-verify`.

## 7. Quyền sửa file và giới hạn
- Được phép sửa và tối ưu **mọi file trong repo, trừ `.env`** (người dùng cho phép ngày 2026-10-10), kể cả `analyze_node.py`, `critic_node.py`, `care_pipeline_service.py`, `data/`, `docs/`, `.github/workflows/`, `docker-compose*.yml`, `deploy/`, `observability/`.
  - Khi sửa luồng lâm sàng/an toàn (analyze, critic, care pipeline, triage): chạy lại `pytest tests/ -m "not integration"`, `eval/triage_eval/run_eval.py --split dev` (+ `etek_dev`) và `eval/triage_eval/metamorphic.py`; không được làm giảm emergency recall.
  - Sửa workflow/deploy/hạ tầng thì nêu rõ trong báo cáo vì ảnh hưởng CI/production của cả nhóm.
- Dữ liệu Supabase dùng chung: sửa qua migration trong `scripts/supabase/migrations/` kèm bản sao lưu + file rollback, chạy lại eval sau khi áp.

## 8. Tuyệt đối không làm
- Luật lâm sàng cứng: không chẩn đoán xác định; không kê đơn/liều thuốc; Zero-Token Emergency Gate phải ngắt ngay và hướng dẫn gọi 115 với ATS 1-2; mỗi lượt chỉ hỏi tối đa 1 câu ngắn.
- Không đọc/sửa/commit/in ra `.env` hay secret.
- Không chạy test `integration` (cần `RUN_LIVE_LLM`, `RUN_LIVE_SUPABASE`, `WORKBENCH_TEST_DATABASE_URL`) nếu người dùng chưa cho phép.
- Không push thẳng `main`; không `--no-verify`.
