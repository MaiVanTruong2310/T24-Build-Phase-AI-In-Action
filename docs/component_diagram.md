# Component Diagram — VCare+ (P-124)

> **Phạm vi:** mô tả các thành phần (component) của hệ thống, trách nhiệm của từng thành phần và cách chúng phụ thuộc/giao tiếp với nhau.
> Luồng dữ liệu theo thời gian (dữ liệu đi qua những bước nào) được mô tả riêng trong **Data Flow Diagram**.
>
> **Căn cứ:** code nhánh `develop` @ `aadaa7f` (02/10/2026). Khi kiến trúc thay đổi, cập nhật lại tài liệu này cùng PR thay đổi code.

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Thành phần bên trong Backend nghiệp vụ](#2-thành-phần-bên-trong-backend-nghiệp-vụ)
3. [Thành phần bên trong AI Agent](#3-thành-phần-bên-trong-ai-agent)
4. [Bảng mô tả thành phần](#4-bảng-mô-tả-thành-phần)
5. [Giao diện giữa các thành phần](#5-giao-diện-giữa-các-thành-phần)
6. [Lưu ý hiện trạng](#6-lưu-ý-hiện-trạng)

**Quy ước màu** dùng chung cho cả 3 sơ đồ:

| Màu | Ý nghĩa |
|---|---|
| 🟦 Xanh dương | Frontend |
| 🟩 Xanh lá | Backend nghiệp vụ |
| 🟪 Tím | AI Agent |
| 🟨 Vàng | Lưu trữ dữ liệu |
| ⬜ Xám | Dịch vụ bên ngoài |

Mũi tên liền là phụ thuộc bắt buộc. Mũi tên nét đứt là phụ thuộc tùy chọn: chỉ chạy khi có cấu hình tương ứng.

---

## 1. Tổng quan hệ thống

Hệ thống gồm 1 ứng dụng frontend (SPA) và 1 ứng dụng backend FastAPI. Bên trong backend có 2 khối: **Backend nghiệp vụ** và **AI Agent**.

```mermaid
flowchart TB
    PAT(["👤 Bệnh nhân"])
    STF(["👤 Lễ tân / Điều phối viên"])

    subgraph FE["Frontend SPA · React 19 + Vite + Redux · Vercel"]
        direction LR
        PUI["Patient Portal<br/>đặt lịch · lịch sử · hồ sơ"]
        CHW["Chatbot Widget<br/>+ Patient Consultation"]
        SUI["Staff Console<br/>duyệt lịch · lịch bác sĩ · danh mục"]
        NB["Notification Bell"]
        APIC["apiClient<br/>cookie session · tự refresh khi 401"]
    end

    subgraph BE["Backend · FastAPI (1 container) · EC2 + Docker Compose"]
        direction TB
        MW["HTTP Layer<br/>CORS · CookieOriginMiddleware · error handlers"]
        subgraph BIZ["Backend nghiệp vụ · src/api + src/services"]
            direction LR
            AUTHC["Auth & User"]
            CATC["Catalog"]
            SCHC["Schedule"]
            BKC["Booking"]
            NTC["Notification"]
        end
        subgraph AI["AI Agent · src/medical_assistant"]
            direction LR
            CHAT["Chat API<br/>+ ChatHistoryService"]
            AGT["Clinical Triage Agent<br/>LangGraph"]
        end
        JOB["Booking Maintenance Loop<br/>chạy nền mỗi 60s"]
    end

    PG[("PostgreSQL 17 + pgvector<br/>container trên EC2")]
    SB[("Supabase<br/>Auth + PostgREST")]
    DL[("Datalake JSONL<br/>data/ · crawl Vinmec")]
    LLM["LLM Providers<br/>OpenRouter → Gemini → OpenAI"]
    SMTP["Gmail SMTP"]
    LSM["LangSmith"]

    PAT --> PUI & CHW
    STF --> SUI
    PUI & CHW & SUI & NB --> APIC
    APIC -->|"HTTPS REST /api/v1<br/>SSE /chat/stream"| MW
    NB <-->|"WSS /notifications/ws"| NTC
    MW --> BIZ & CHAT
    CHAT --> AGT
    BKC --> NTC
    JOB --> BKC & NTC
    BIZ -->|"SQLAlchemy async"| PG
    CHAT -->|"chat_conversations<br/>chat_turns"| PG
    AGT -.->|"PostgREST: doctors,<br/>doctor_schedules, booking_requests"| SB
    AUTHC -.->|"Auth API khi<br/>AUTH_PROVIDER=supabase"| SB
    AGT -->|"đọc file"| DL
    AGT -->|"OpenAI-compatible API"| LLM
    NTC -->|"SMTP :587"| SMTP
    AGT -.->|"trace"| LSM

    classDef fe fill:#dbeafe,stroke:#2563eb,color:#0b1f4d
    classDef be fill:#dcfce7,stroke:#16a34a,color:#0a2e16
    classDef ai fill:#ede9fe,stroke:#7c3aed,color:#2a1260
    classDef store fill:#fef3c7,stroke:#d97706,color:#3d2600
    classDef ext fill:#f1f5f9,stroke:#64748b,color:#1e293b
    class PUI,CHW,SUI,NB,APIC fe
    class MW,AUTHC,CATC,SCHC,BKC,NTC,JOB be
    class CHAT,AGT ai
    class PG,SB,DL store
    class LLM,SMTP,LSM ext
```

---

## 2. Thành phần bên trong Backend nghiệp vụ

Backend nghiệp vụ chia **4 tầng**: Endpoint → Service → Repository → Model. Endpoint không truy vấn DB trực tiếp mà gọi Service; endpoint chỉ import Model để khai báo kiểu, ví dụ `User`. Mỗi module (Auth, Catalog, Booking, Notification) là một "lát dọc" đi qua cả 4 tầng.

```mermaid
flowchart TB
    subgraph L1["① Tầng API · src/api/endpoints  (+ tác vụ nền trong main.py)"]
        direction LR
        E_AUTH["auth.py<br/>/auth/* · /users/*"]
        E_CAT["doctor · facility · service<br/>specialty · catalog_common<br/>/doctors /services ... · /staff/*"]
        E_SCH["schedule.py<br/>/doctors/{id}/availability<br/>/staff/schedules"]
        E_BK["booking.py<br/>/bookings · /staff/bookings"]
        E_NT["notification.py<br/>/notifications · /notifications/ws"]
        JOB["main.py<br/>_booking_maintenance_loop"]
    end

    subgraph L2["② Tầng nghiệp vụ · src/services"]
        direction LR
        S_AUTH["AuthService · OtpProvider<br/>supabase_auth · cookie_session"]
        S_CAT["CatalogService<br/>Doctor/Facility/Specialty/<br/>MedicalService mixins"]
        S_SCH["ScheduleServiceMixin"]
        S_BK["BookingService"]
        S_NT["NotificationService<br/>GmailEmailSender<br/>NotificationConnectionManager"]
    end

    subgraph L3["③ Tầng truy cập dữ liệu · src/repositories"]
        direction LR
        R_AUTH["AuthRepository<br/>UserRepository"]
        R_CAT["CatalogRepository<br/>+ Audit mixin"]
        R_BK["BookingRepository"]
        R_NT["NotificationRepository"]
    end

    subgraph L4["④ Tầng mô hình · src/models · migration alembic 0001 → 0018"]
        direction LR
        M_USR["User · OtpChallenge<br/>RefreshSession"]
        M_CAT["Specialty · Doctor · Facility<br/>Service · DoctorSchedule<br/>CatalogAuditEvent"]
        M_BK["Booking"]
        M_NT["Notification"]
    end

    CORE["src/core<br/>security: scrypt + JWT · exceptions · logging"]
    PG[("PostgreSQL<br/>qua src/db/session.py")]

    E_AUTH --> S_AUTH --> R_AUTH --> M_USR
    E_CAT --> S_CAT --> R_CAT --> M_CAT
    E_SCH --> S_SCH --> R_CAT
    E_BK --> S_BK --> R_BK --> M_BK
    E_NT --> S_NT --> R_NT --> M_NT
    JOB --> S_BK
    S_BK -->|"tạo thông báo khi<br/>đặt · duyệt · hủy"| S_NT
    S_AUTH --> CORE
    L4 --> PG

    classDef be fill:#dcfce7,stroke:#16a34a,color:#0a2e16
    classDef store fill:#fef3c7,stroke:#d97706,color:#3d2600
    class E_AUTH,E_CAT,E_SCH,E_BK,E_NT,JOB,S_AUTH,S_CAT,S_SCH,S_BK,S_NT,R_AUTH,R_CAT,R_BK,R_NT,M_USR,M_CAT,M_BK,M_NT,CORE be
    class PG store
```

**Phân quyền:**
- Mọi endpoint dưới `/staff/*` đều đi qua `require_staff`.
- Các endpoint còn lại (xem danh mục, xem lịch trống, đặt/hủy/đổi lịch) chỉ yêu cầu đăng nhập qua `get_current_user`.
- `require_patient` đã được định nghĩa trong `dependencies.py` nhưng chưa route nào dùng.
- Token được đọc từ header `Authorization: Bearer` hoặc từ cookie `p124_access`.

---

## 3. Thành phần bên trong AI Agent

Agent là một đồ thị LangGraph 3 node. Phần lớn logic nằm trong các **domain service** mà node `analyze` gọi lần lượt.

```mermaid
flowchart TB
    subgraph API["Chat API · medical_assistant/api/routes.py"]
        direction LR
        R_CHAT["POST /chat<br/>POST /chat/stream (SSE)"]
        R_HIS["GET /chat/conversations<br/>GET /chat/conversations/{id}"]
        R_BR["POST /booking-requests"]
    end

    CHS["ChatHistoryService · src/services/chat_history.py<br/>lưu lượt chat · nạp hồ sơ sức khỏe"]

    subgraph GRAPH["LangGraph · agent/graph.py · checkpointer: MemorySaver"]
        direction LR
        N1["① analyze"] --> N2["② find_doctors"] --> N3["③ respond"]
        N1 -->|"kết thúc sớm"| N3
    end

    subgraph DOM["Domain services · medical_assistant/domain"]
        direction LR
        G_SAFE["(a) An toàn<br/>SecurityGuardrailService · DLP<br/>Deobfuscator<br/>ClinicalTriageService (cấp cứu, ATS)"]
        G_DIA["(b) Hiểu hội thoại<br/>ZeroTokenCacheService (FAQ)<br/>ClinicalGuardrailService (intent)<br/>HybridDialogueService<br/>LLMClinicalExtractor"]
        G_CLI["(c) Lâm sàng<br/>ClinicalFactService<br/>ClinicalNegationService<br/>DynamicProbingService<br/>SpecialtyRouter"]
        G_DOC["Tìm bác sĩ<br/>DoctorScheduleService"]
        G_RES["Soạn trả lời<br/>ClinicalGuardrailService<br/>FacilityService<br/>language_service (disclaimer)"]
        G_BR["BookingRequestService"]
    end

    RAG["RagStore · rag/<br/>SQLite FTS"]
    LLMF["FailoverChatModel<br/>infrastructure/llm.py"]

    PG[("PostgreSQL<br/>chat_conversations · chat_turns · users")]
    SB[("Supabase PostgREST<br/>doctors · doctor_schedules · booking_requests")]
    DL[("Datalake JSONL")]
    LLM["LLM Providers"]

    R_CHAT --> CHS
    R_HIS --> CHS
    R_CHAT --> N1
    R_BR --> G_BR
    CHS --> PG
    N1 --> G_CLI & G_DIA & G_SAFE
    N2 --> G_DOC
    N3 --> G_RES
    G_DIA --> LLMF --> LLM
    G_RES --> RAG --> DL
    G_DOC -.->|"có SUPABASE_URL"| SB
    G_DOC -->|"không có: dữ liệu crawl"| DL
    G_BR -.-> SB

    classDef ai fill:#ede9fe,stroke:#7c3aed,color:#2a1260
    classDef store fill:#fef3c7,stroke:#d97706,color:#3d2600
    classDef ext fill:#f1f5f9,stroke:#64748b,color:#1e293b
    class R_CHAT,R_HIS,R_BR,CHS,N1,N2,N3,G_SAFE,G_DIA,G_CLI,G_DOC,G_RES,G_BR,RAG,LLMF ai
    class PG,SB,DL store
    class LLM ext
```

**Cách đọc:**
- Node `analyze` gọi 3 nhóm service theo thứ tự **(a) → (b) → (c)**:
  - (a) An toàn: bảo mật đầu vào, rồi kiểm tra cấp cứu.
  - (b) Hiểu hội thoại: cache FAQ, intent/guardrail, rồi LLM.
  - (c) Lâm sàng: trích dữ kiện, xử lý phủ định, hỏi thêm, chọn chuyên khoa.
- Ở bất kỳ bước nào, nếu gặp ca cấp cứu, bị chặn, câu FAQ, hay cần hỏi thêm, đồ thị sẽ **kết thúc sớm** và đi thẳng tới `respond`, bỏ qua `find_doctors`.
- Các nhóm service là module Python được gọi trực tiếp trong cùng tiến trình, không phải service mạng riêng.

---

## 4. Bảng mô tả thành phần

### Frontend (`frontend/`)

| Thành phần | Code | Trách nhiệm |
|---|---|---|
| Patient Portal | `pages/AppointmentBooking`, `AppointmentHistory`, `AppointmentDetail`, `AppointmentProgress`, `PatientProfile`, `PatientDepartments` | Đặt lịch, theo dõi trạng thái lịch, quản lý hồ sơ sức khỏe |
| Chatbot Widget | `layouts/ChatbotWidget.tsx`, `pages/PatientConsultation`, `features/chat/api.ts` | Hội thoại với agent qua SSE, gửi yêu cầu đặt lịch từ chat |
| Staff Console | `pages/StaffDashboard`, `AppointmentApproval`, `ScheduleApprove`, `DoctorSchedule`, `DoctorManagement`, `ServiceManagement`, `ChatTakeover`, `EmergencyCoordinator` | Duyệt lịch, quản lý lịch bác sĩ và danh mục, điều phối |
| Notification Bell | `features/notification/` | Nhận thông báo realtime qua WebSocket, đánh dấu đã đọc |
| apiClient | `app/apiClient.ts` | Gọi `/api/v1`, gửi cookie session, tự refresh token khi gặp 401 |

### Backend nghiệp vụ (`src/`)

| Thành phần | Code | Trách nhiệm | Phụ thuộc |
|---|---|---|---|
| HTTP Layer | `main.py`, `api/handlers.py`, `services/cookie_session.py` | CORS; chặn request ghi dữ liệu dùng cookie nếu `Origin` không nằm trong danh sách cho phép; chuẩn hóa lỗi | — |
| Auth & User | `api/endpoints/auth.py`, `services/auth.py`, `services/otp.py`, `services/supabase_auth.py`, `core/security.py` | Đăng ký, OTP, đăng nhập, refresh token, phiên đăng nhập, hồ sơ người dùng | PostgreSQL; Supabase Auth (tùy chọn) |
| Catalog | `api/endpoints/catalog*.py`, `doctor.py`, `facility.py`, `service.py`, `specialty.py`, `services/catalog.py` | CRUD khoa, bác sĩ, dịch vụ, cơ sở; ghi audit log | PostgreSQL |
| Schedule | `api/endpoints/schedule.py`, `services/schedule.py` | Lịch làm việc của bác sĩ, chống trùng giờ, import hàng loạt | Catalog |
| Booking | `api/endpoints/booking.py`, `services/booking.py` | Tạo, hủy, đổi lịch; lễ tân duyệt/từ chối (`pending_approval` → `confirmed`/`rejected`) | Schedule, Catalog, Notification |
| Notification | `api/endpoints/notification.py`, `services/notification.py`, `services/email.py`, `realtime/notifications.py` | Thông báo trong app, đẩy WebSocket, hàng đợi email | PostgreSQL, Gmail SMTP |
| Booking Maintenance Loop | `main.py · _booking_maintenance_loop` | Chạy nền: cho booking quá hạn hết hạn, tạo nhắc lịch, gửi email đang chờ | Booking, Notification |

### AI Agent (`src/medical_assistant/`)

| Thành phần | Code | Trách nhiệm | Phụ thuộc |
|---|---|---|---|
| Chat API | `api/routes.py` | Nhận tin nhắn, stream phản hồi (SSE), trả lịch sử hội thoại, nhận yêu cầu đặt lịch | Agent, ChatHistoryService |
| ChatHistoryService | `src/services/chat_history.py` | Với người đã đăng nhập: lưu từng lượt chat, lưu và khôi phục state rút gọn, nạp hồ sơ sức khỏe vào agent | PostgreSQL (bảng tạo bằng `scripts/sql/chat_history.sql`) |
| Clinical Triage Agent | `agent/graph.py`, `agent/nodes/`, `agent/state.py` | Điều phối 3 node `analyze` → `find_doctors` → `respond` | Domain services |
| Security Guardrail | `domain/security/` | Chặn prompt injection, che PII, gỡ chữ bị làm rối | — |
| Triage | `domain/triage_service.py`, `domain/disease_triage.py` | Phát hiện cấp cứu (red flag), chấm mức ATS | — |
| Clinical Guardrail | `domain/guardrail_service.py` | Nhận diện intent, từ chối chẩn đoán/kê thuốc, trả lời thông tin khoa | RagStore |
| Dialogue & Facts | `domain/hybrid_dialogue_service.py`, `llm_clinical_extractor.py`, `clinical_fact_service.py`, `clinical_negation_service.py`, `probing_service.py` | Hiểu hội thoại bằng LLM, trích triệu chứng, xử lý phủ định, sinh câu hỏi làm rõ | LLM |
| Specialty Router | `domain/specialty_router.py` | Chọn chuyên khoa phù hợp từ triệu chứng | — |
| Doctor Schedule | `domain/doctor_schedule_service.py` | Tìm bác sĩ và khung giờ trống | Supabase hoặc Datalake |
| Booking Request | `domain/booking_request_service.py` | Lưu yêu cầu đặt lịch từ chat vào hàng đợi `booking_requests` | Supabase |
| RAG | `rag/service.py`, `rag/store_cache.py` | Tìm kiếm full-text trên dữ liệu JSONL, trả kèm nguồn | Datalake |
| LLM Gateway | `infrastructure/llm.py` | Gọi LLM qua API tương thích OpenAI, tự chuyển provider khi lỗi | OpenRouter / Gemini / OpenAI |
| Ingestion (offline) | `ingestion/` | Crawl và chuẩn hóa dữ liệu Vinmec (bác sĩ, khoa, dịch vụ, bệnh viện, bệnh) thành JSONL | — |

---

## 5. Giao diện giữa các thành phần

| Từ | Đến | Giao thức | Điểm cuối / cơ chế |
|---|---|---|---|
| Frontend | Backend | HTTPS REST | `/api/v1/*`, xác thực bằng cookie `p124_access`/`p124_refresh` hoặc header `Bearer` |
| Chatbot Widget | Chat API | Server-Sent Events | `POST /api/v1/chat/stream`: event `init` → `token` → `metadata` → `[DONE]` |
| Notification Bell | Notification | WebSocket | `/api/v1/notifications/ws` |
| Booking | Notification | Gọi hàm trong cùng tiến trình | `NotificationService.create_for_booking_*` |
| Notification | Bell đang mở | WebSocket push | `NotificationConnectionManager.publish(user_id, payload)` |
| Backend nghiệp vụ, ChatHistory | PostgreSQL | SQLAlchemy async (psycopg 3) | `DATABASE_URL` |
| Agent | Supabase | HTTP PostgREST | `SUPABASE_URL/rest/v1/{table}` (tùy chọn) |
| Auth | Supabase | HTTP | `SUPABASE_URL/auth/v1/*` khi `AUTH_PROVIDER=supabase` |
| Agent | LLM | HTTPS, OpenAI-compatible | Thứ tự dự phòng OpenRouter → Gemini → OpenAI |
| Notification | Gmail | SMTP STARTTLS :587 | `GMAIL_SMTP_*` |

---

## 6. Lưu ý hiện trạng

Các điểm dưới đây giúp người đọc hiểu đúng sơ đồ. Chúng là hiện trạng của code, không phải thiết kế mong muốn.

1. **Hai nguồn dữ liệu bác sĩ.**
   - Backend nghiệp vụ dùng bảng `doctors` / `doctor_schedules` trong PostgreSQL (schema do Alembic quản lý).
   - Agent đọc bảng `doctors` bên Supabase. Bảng này có thêm các trường crawl như `source_profile`, `source_system`, `external_id`.
   - Hai bảng không đồng bộ với nhau. Yêu cầu đặt lịch từ chat ghi vào `booking_requests` (Supabase), không vào `bookings` mà trang duyệt lịch đang đọc.
2. **Bộ nhớ hội thoại có 2 lớp.**
   - LangGraph dùng `MemorySaver`, lưu trong RAM.
   - Với người **đã đăng nhập**, `ChatHistoryService` lưu thêm một bản rút gọn của state (các trường trong `STATE_FIELDS`) vào cột `chat_conversations.checkpoint` (jsonb) và nạp lại ở mỗi lượt, nên restart server không mất ngữ cảnh.
   - Với **khách chưa đăng nhập**, state chỉ nằm trong RAM và sẽ mất khi restart.
3. **WebSocket thông báo được giữ trong RAM** của tiến trình. Chạy nhiều instance backend thì thông báo realtime chỉ tới được người đang kết nối vào đúng instance đó.
4. **Chat Takeover** đã có bảng (migration `0018_chat_takeover`), nhưng chưa có API. Giao diện `pages/ChatTakeover` đang dùng dữ liệu mẫu (`mockData.ts`).
5. **Bảng `chat_conversations`, `chat_turns`** được tạo bằng script `scripts/sql/chat_history.sql`, không qua Alembic.
6. **Code không còn được dùng.** Ứng dụng thực tế khởi động từ `src/main.py`. Các file sau không nằm trên đường chạy và không được vẽ trong sơ đồ:
   - `src/api/routes.py` + `src/agents/`: agent mẫu của template. Router này không được `main.py` gắn vào.
   - `src/models/tables.py`: schema cũ dùng id kiểu int, không còn được import.
   - `src/medical_assistant/main.py`: app chạy riêng cũ của chatbot.
