# 🚀 KẾ HOẠCH TRIỂN KHAI PRODUCTION — P-124 AI Medical Assistant

**Trạng thái hiện tại:** 145/145 tests passed ✅ | Security Guardrails 4 tầng ✅ | 741 mặt bệnh + 992 bác sĩ ✅

---

## 📊 TỔNG QUAN HIỆN TRẠNG & GAP ANALYSIS

### ✅ Đã hoàn thành (Production-Ready)
| Module | Trạng thái | File chính |
|:---|:---:|:---|
| Safety Engine v3 (ATS 1-5, 741 bệnh) | ✅ DONE | [triage_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/triage_service.py) |
| Clinical Guardrails (SAF-01/02) | ✅ DONE | [guardrail_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/guardrail_service.py) |
| Security Guardrails 4 tầng (De-obfuscation + DLP + Anti-Injection) | ✅ DONE | [security/](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/security) |
| Adaptive Probing (2 turns max) | ✅ DONE | [probing_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/probing_service.py) |
| Zero-Token Cache & Token Metrics | ✅ DONE | [cache_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/cache_service.py), [token_counter.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/token_counter.py) |
| Doctor & Slot Discovery (992 bác sĩ) | ✅ DONE | [doctor_schedule_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/doctor_schedule_service.py) |
| Bilingual EN-VI Pipeline | ✅ DONE | [language_service.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/language_service.py) |
| SSE Streaming | ✅ DONE | [routes.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/api/routes.py) |
| LangGraph 3-Node StateGraph | ✅ DONE | [graph.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/agent/graph.py) |
| Specialty Router v2.0 (3 tầng) | ✅ DONE | [specialty_router.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/specialty_router.py) |

### ❌ Gaps cần đóng trước Production
| Gap | Mức độ | Mô tả |
|:---|:---:|:---|
| **G1. Dockerization** | P0 | Chưa có Dockerfile, docker-compose |
| **G2. Persistent Session (PostgresSaver)** | P0 | Đang dùng `MemorySaver` (in-memory, mất khi restart) |
| **G3. Environment & Secrets Management** | P0 | `.env` cần chuẩn hóa cho multi-env |
| **G4. Rate Limiting & Auth** | P0 | Chưa có auth middleware, rate limiter |
| **G5. Structured Logging & Observability** | P1 | `print()` đang dùng thay vì structured logger |
| **G6. Health Check Readiness** | P1 | `/health` chưa kiểm tra dependencies |
| **G7. CI/CD Pipeline** | P1 | Chưa có GitHub Actions / automated deploy |
| **G8. HITL Dispatcher Dashboard** | P2 | Planned cho Sprint 3 |
| **G9. Realtime Notifications** | P2 | Chưa tích hợp Supabase Realtime cho lễ tân |
| **G10. Load Testing** | P2 | Chưa có benchmark 10K CCU |

---

## 🗂️ KẾ HOẠCH 7 BƯỚC TRIỂN KHAI CHI TIẾT

---

### 📦 BƯỚC 1: DOCKERIZATION & INFRASTRUCTURE (Ước tính: 2-3 giờ)

> **Mục tiêu:** Container hóa toàn bộ ứng dụng, đảm bảo chạy đồng nhất trên mọi môi trường.

#### 1.1 Tạo `Dockerfile`
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src/ src/
COPY data/datalake/ data/datalake/

# Non-root user for security
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.medical_assistant.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

#### 1.2 Tạo `docker-compose.yml`
```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env.production
    environment:
      - APP_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    restart: unless-stopped
```

#### 1.3 Tạo `.dockerignore`
```
.env
.git/
__pycache__/
*.pyc
tests/
docs/
eval_output/
scripts/
.pytest_cache/
context_agent/
```

#### 1.4 Files cần tạo/sửa:
| File | Hành động | Vị trí |
|:---|:---|:---|
| `Dockerfile` | **Tạo mới** | `Dockerfile` |
| `docker-compose.yml` | **Tạo mới** | `docker-compose.yml` |
| `.dockerignore` | **Tạo mới** | `.dockerignore` |
| `requirements.txt` | **Kiểm tra/cập nhật** | `requirements.txt` |

---

### 🔐 BƯỚC 2: PERSISTENT SESSION & SECRETS (Ước tính: 2-3 giờ)

> **Mục tiêu:** Chuyển từ `MemorySaver` → `PostgresSaver` để session không mất khi container restart.

#### 2.1 Chuyển đổi Checkpointer
**File cần sửa:** [graph.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/agent/graph.py)

```python
# TRƯỚC (in-memory, mất khi restart)
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# SAU (persistent, tồn tại qua restart)
import os
from langgraph.checkpoint.memory import MemorySaver

def get_checkpointer():
    """Factory pattern: Dùng PostgresSaver khi production, MemorySaver khi dev/test."""
    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        db_url = os.getenv("CHECKPOINT_DATABASE_URL")
        return AsyncPostgresSaver.from_conn_string(db_url)
    return MemorySaver()

checkpointer = get_checkpointer()
```

#### 2.2 Chuẩn hóa Environment Variables
**File cần tạo:** `.env.production.example`

```env
# App
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com

# LLM
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini
LLM_TEMPERATURE=0.3

# Database (Supabase)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...
DATABASE_URL=postgresql://postgres:...@db.xxxxx.supabase.co:5432/postgres

# Checkpointer (LangGraph Session Persistence)
CHECKPOINT_DATABASE_URL=postgresql://postgres:...@db.xxxxx.supabase.co:5432/postgres

# Security
SECRET_KEY=your-random-secret-for-jwt-signing
API_KEY_HEADER=X-API-Key
```

#### 2.3 Tạo migration cho bảng checkpointer
```sql
-- Bảng này được LangGraph PostgresSaver tự tạo, nhưng cần đảm bảo user có quyền
GRANT CREATE ON SCHEMA public TO postgres;
-- PostgresSaver sẽ tạo bảng: checkpoints, checkpoint_blobs, checkpoint_writes
```

#### 2.4 Files cần sửa:
| File | Hành động |
|:---|:---|
| [graph.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/agent/graph.py) | Sửa checkpointer factory |
| [config.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/config.py) | Thêm `checkpoint_database_url`, `secret_key`, `api_key_header` |
| `.env.production.example` | Tạo mới |

---

### 🛡️ BƯỚC 3: AUTH, RATE LIMITING & MIDDLEWARE (Ước tính: 3-4 giờ)

> **Mục tiêu:** Bảo vệ API endpoint khỏi lạm dụng, xác thực người dùng.

#### 3.1 API Key Middleware
**File cần tạo:** `src/medical_assistant/api/middleware.py`

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from src.medical_assistant.config import get_settings

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Xác thực API Key cho mọi request tới /api/v1/*."""
    
    EXEMPT_PATHS = {"/health", "/", "/docs", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        settings = get_settings()
        if settings.app_env == "development":
            return await call_next(request)
        
        api_key = request.headers.get(settings.api_key_header)
        if not api_key or api_key != settings.secret_key:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        return await call_next(request)
```

#### 3.2 Rate Limiter (In-Memory hoặc Redis-backed)
```python
import time
from collections import defaultdict

class RateLimiter:
    """Sliding window rate limiter: max N requests per window_seconds per session."""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, session_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._timestamps[session_id] = [
            t for t in self._timestamps[session_id] if t > cutoff
        ]
        if len(self._timestamps[session_id]) >= self.max_requests:
            return False
        self._timestamps[session_id].append(now)
        return True
```

#### 3.3 Request Validation & Size Limit
```python
# Trong routes.py - thêm validation vào ChatRequest
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)  # Chống payload lớn
    session_id: str = Field(..., min_length=1, max_length=128)
```

#### 3.4 Files cần tạo/sửa:
| File | Hành động |
|:---|:---|
| `api/middleware.py` | **Tạo mới** — API Key + Rate Limiter |
| [main.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/main.py) | Sửa — thêm middleware |
| [schemas.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/domain/schemas.py) | Sửa — thêm length validation |

---

### 📝 BƯỚC 4: STRUCTURED LOGGING & OBSERVABILITY (Ước tính: 3-4 giờ)

> **Mục tiêu:** Thay thế `print()` bằng structured JSON logging, hỗ trợ audit trail cho sự kiện security.

#### 4.1 Thiết lập Logger Service
**File cần tạo:** `src/medical_assistant/infrastructure/logger.py`

```python
import logging
import json
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Structured JSON formatter cho production logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Đính kèm extra fields (session_id, violation_type, etc.)
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
        return json.dumps(log_entry, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

#### 4.2 Các điểm cần instrument
| Sự kiện | Log Level | Data fields |
|:---|:---:|:---|
| Request nhận được | INFO | `session_id`, `message_length`, `language` |
| Security BLOCKED | **WARNING** | `session_id`, `violation_type`, `detected_technique`, `matched_pattern` |
| Emergency Red Flag | **CRITICAL** | `session_id`, `ats_level`, `triggered_rules`, `query_excerpt` |
| DLP Leakage Detected | **ERROR** | `session_id`, `redacted_count`, `redacted_types` |
| Cache Hit (Zero-Token) | INFO | `session_id`, `faq_key`, `tokens_saved` |
| Doctor Search | INFO | `session_id`, `specialty`, `doctors_found` |
| Slot Hold Created | INFO | `session_id`, `booking_code`, `slot_id` |
| LLM Call | INFO | `session_id`, `model`, `prompt_tokens`, `completion_tokens`, `latency_ms` |
| Request hoàn thành | INFO | `session_id`, `total_latency_ms`, `workflow_status` |

#### 4.3 Tích hợp LangSmith (Optional nhưng rất khuyến nghị)
```python
# Trong .env.production
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=p124-medical-assistant
```

#### 4.4 Files cần tạo/sửa:
| File | Hành động |
|:---|:---|
| `infrastructure/logger.py` | **Tạo mới** |
| [example_node.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/agent/nodes/example_node.py) | Sửa — thêm logging cho Security, Emergency, Cache events |
| [routes.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/api/routes.py) | Sửa — thêm request/response logging |
| [main.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/main.py) | Sửa — cấu hình root logger |

---

### ❤️ BƯỚC 5: PRODUCTION-READY HEALTH CHECKS (Ước tính: 1-2 giờ)

> **Mục tiêu:** Health endpoint kiểm tra đầy đủ dependencies, hỗ trợ container orchestration.

#### 5.1 Nâng cấp Health Endpoint
**File cần sửa:** [main.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/main.py) hoặc [routes.py](file:///d:/AI%20in%20Action/LogAgent/P-124/src/medical_assistant/api/routes.py)

```python
@app.get("/health")
async def health():
    """Readiness probe: kiểm tra toàn bộ dependencies."""
    checks = {
        "app": "ok",
        "datalake_diseases": "unknown",
        "datalake_doctors": "unknown",
        "openai_key_configured": "unknown",
        "supabase_configured": "unknown",
    }
    
    # Check Datalake files
    from pathlib import Path
    diseases_path = Path("data/datalake/normalized/diseases_triaged.jsonl")
    doctors_path = Path("data/datalake/normalized/vinmec_professionals_vi.jsonl")
    checks["datalake_diseases"] = "ok" if diseases_path.exists() else "missing"
    checks["datalake_doctors"] = "ok" if doctors_path.exists() else "missing"
    
    # Check API keys configured
    settings = get_settings()
    checks["openai_key_configured"] = "ok" if settings.openai_api_key else "missing"
    checks["supabase_configured"] = "ok" if settings.supabase_url else "not_configured"
    
    overall = "ok" if all(
        v in ("ok", "not_configured") for v in checks.values()
    ) else "degraded"
    
    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        {"status": overall, "env": settings.app_env, "checks": checks},
        status_code=status_code
    )

@app.get("/health/live")
async def liveness():
    """Liveness probe: chỉ kiểm tra app đang chạy."""
    return {"status": "alive"}
```

---

### 🔄 BƯỚC 6: CI/CD PIPELINE (Ước tính: 2-3 giờ)

> **Mục tiêu:** Tự động hóa kiểm thử và deployment khi push code.

#### 6.1 GitHub Actions Workflow
**File cần tạo:** `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline P-124

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          
      - name: Install dependencies
        working-directory: 
        run: |
          pip install -r requirements.txt
          pip install pytest
          
      - name: Run full test suite (145 tests)
        working-directory: 
        run: python -m pytest tests/ -v --tb=short
        
      - name: Verify 100% pass rate
        working-directory: 
        run: |
          RESULT=$(python -m pytest tests/ --tb=no -q 2>&1 | tail -1)
          echo "$RESULT"
          if echo "$RESULT" | grep -q "failed"; then
            echo "❌ Test suite has failures!"
            exit 1
          fi
          echo "✅ All tests passed!"
          
  security-scan:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Check for hardcoded secrets
        run: |
          # Scan for common secret patterns
          if grep -rn "sk-[a-zA-Z0-9]" --include="*.py" src/; then
            echo "❌ Hardcoded OpenAI key detected!"
            exit 1
          fi
          echo "✅ No hardcoded secrets found"

  docker-build:
    runs-on: ubuntu-latest
    needs: [test, security-scan]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        working-directory: 
        run: docker build -t p124-medical-assistant:latest .
        
      - name: Test Docker health
        working-directory: 
        run: |
          docker run -d --name test-app \
            -e APP_ENV=test \
            -e OPENAI_API_KEY=test \
            -p 8000:8000 p124-medical-assistant:latest
          sleep 5
          curl -f http://localhost:8000/health/live || exit 1
          docker stop test-app
```

---

### 🌐 BƯỚC 7: DEPLOYMENT & CLOUD HOSTING (Ước tính: 2-4 giờ)

> **Mục tiêu:** Triển khai lên cloud platform, sẵn sàng cho Demo Day.

#### 7.1 Lựa chọn Platform

| Platform | Ưu điểm | Nhược điểm | Phù hợp |
|:---|:---|:---|:---:|
| **Render.com** | Free tier, Docker native, auto HTTPS, dễ setup | Cold start ~30s trên free tier | ⭐⭐⭐⭐ |
| **Railway.app** | GitHub deploy, Postgres built-in, rất nhanh | Chi phí phát sinh khi scale | ⭐⭐⭐⭐ |
| **Google Cloud Run** | Serverless, pay-per-use, auto-scale | Cần GCP account, setup phức tạp hơn | ⭐⭐⭐ |
| **Fly.io** | Edge computing, global CDN, Docker native | Cần credit card | ⭐⭐⭐ |

#### 7.2 Render.com Deployment (Khuyến nghị cho Demo)
**File cần tạo:** `render.yaml`

```yaml
services:
  - type: web
    name: p124-medical-assistant
    runtime: docker
    plan: starter  # hoặc free
    healthCheckPath: /health/live
    envVars:
      - key: APP_ENV
        value: production
      - key: OPENAI_API_KEY
        sync: false  # Nhập thủ công trên Dashboard
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: SECRET_KEY
        generateValue: true
```

#### 7.3 Kiến trúc Production Topology

```mermaid
graph TB
    subgraph Internet["🌐 Internet"]
        User["👤 Bệnh nhân (Browser/Mobile)"]
    end
    
    subgraph CloudPlatform["☁️ Cloud Platform (Render/Railway)"]
        LB["🔒 HTTPS Load Balancer + Auto TLS"]
        
        subgraph App["📦 Docker Container"]
            FastAPI["FastAPI + Uvicorn"]
            Middleware["Auth + Rate Limiter"]
            Agent["LangGraph Agent (3-Node)"]
            Security["Security Guardrails 4 tầng"]
            Triage["Triage Engine + 741 bệnh"]
            Cache["Zero-Token Cache"]
        end
    end
    
    subgraph External["🔌 External Services"]
        OpenAI["OpenAI GPT-4o-mini API"]
        Supabase["Supabase PostgreSQL + RLS"]
    end
    
    User -->|HTTPS| LB
    LB --> FastAPI
    FastAPI --> Middleware --> Agent
    Agent --> Security & Triage & Cache
    Agent -->|API Call| OpenAI
    Agent -->|PostgREST| Supabase
```

---

## ⏱️ TIMELINE TỔNG HỢP

```mermaid
gantt
    title Lộ trình Production Deployment P-124
    dateFormat  YYYY-MM-DD
    
    section Bước 1: Docker
    Dockerfile & docker-compose           :b1, 2026-09-30, 1d
    
    section Bước 2: Persistent Session
    PostgresSaver + Secrets Management    :b2, after b1, 1d
    
    section Bước 3: Auth & Security
    API Key + Rate Limiter + Middleware   :b3, after b2, 1d
    
    section Bước 4: Logging
    Structured JSON Logger + Audit Trail  :b4, after b3, 1d
    
    section Bước 5: Health Checks
    Readiness/Liveness Probes            :b5, after b4, 1d
    
    section Bước 6: CI/CD
    GitHub Actions Pipeline              :b6, after b5, 1d
    
    section Bước 7: Deploy
    Cloud Deployment + DNS + HTTPS       :b7, after b6, 1d
    
    section QA
    Smoke Test & Monitoring Setup        :qa, after b7, 1d
```

---

## 🎯 CHECKLIST TRƯỚC KHI GO-LIVE

```
[ ] 145/145 tests passed trên CI
[ ] Docker build thành công & health check OK
[ ] PostgresSaver hoạt động (session survive restart)
[ ] API Key middleware kích hoạt trên production
[ ] Rate limiter hoạt động (30 req/min/session)
[ ] Structured logging ghi đúng format JSON
[ ] Security events (BLOCKED, DLP) ghi vào log
[ ] OpenAI API key KHÔNG có trong code/image
[ ] CORS chỉ allow domain production
[ ] Health endpoint kiểm tra tất cả dependencies
[ ] SSL/TLS (HTTPS) hoạt động
[ ] LangSmith tracing kích hoạt (optional)
[ ] Smoke test: Luồng triệu chứng → bác sĩ → đặt slot
[ ] Smoke test: Cấp cứu → chặn đặt lịch → gọi 115
[ ] Smoke test: Prompt injection → SECURITY_BLOCKED
[ ] Smoke test: Hỏi thuốc → GUARDRAIL_MEDICATION
```

---

## 📌 GHI CHÚ QUAN TRỌNG

> [!IMPORTANT]
> **Thứ tự triển khai là bắt buộc:** Bước 1 → 2 → 3 → 4 → 5 → 6 → 7. Mỗi bước xây dựng trên nền tảng của bước trước.

> [!WARNING]
> **Quy tắc vàng:** Mọi code commit chỉ được coi là hợp lệ khi toàn bộ **145/145 tests passed (100%)**. Không được deploy nếu bất kỳ test nào fail.

> [!TIP]
> Nếu muốn triển khai nhanh nhất cho Demo Day, có thể **gộp Bước 1-5 thành 1 phiên** (~8-10 giờ) rồi deploy ngay.
