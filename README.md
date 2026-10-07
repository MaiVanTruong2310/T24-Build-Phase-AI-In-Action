# 🏥 VCare+ — Vinmec Smart Medical Assistant (VMEC-01 / P-124)

> **Trợ lý Tiếp đón Y tế & Điều phối Khám Bệnh Thông minh Đa tác tử (Multi-Agent System)**  
> *Phân tầng cấp cứu ATS • Tự động phân luồng chuyên khoa • Đặt lịch qua hội thoại tự nhiên • Human-in-the-Loop Workbench*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6F00?style=flat&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Mục lục

- [1. Giới thiệu tổng quan](#1-giới-thiệu-tổng-quan)
- [2. Các tính năng cốt lõi](#2-các-tính-năng-cốt-lõi)
- [3. Kiến trúc hệ thống & Luồng xử lý](#3-kiến-trúc-hệ-thống--luồng-xử-lý)
- [4. Bảng biến môi trường (Environment Variables)](#4-bảng-biến-môi-trường-environment-variables)
- [5. Hướng dẫn cài đặt & Chạy dự án (Setup Instructions)](#5-hướng-dẫn-cài-đặt--chạy-dự-án-setup-instructions)
- [6. Kịch bản & Câu hỏi mẫu (Sample Queries)](#6-kịch-bản--câu-hỏi-mẫu-sample-queries)
- [7. Danh mục API Endpoints](#7-danh-mục-api-endpoints)
- [8. Kiểm thử & Đảm bảo chất lượng (Testing)](#8-kiểm-thử--đảm-bảo-chất-lượng-testing)
- [9. Cấu trúc thư mục dự án](#9-cấu-trúc-thư-mục-dự-án)
- [10. Đóng góp & Bản quyền](#10-đóng-góp--bản-quyền)

---

## 1. Giới thiệu tổng quan

**Vinmec Smart Medical Assistant** là giải pháp trợ lý ảo y tế toàn diện được xây dựng nhằm giải quyết bài toán quá tải tiếp đón bệnh nhân tại các bệnh viện và phòng khám đa khoa tiêu chuẩn quốc tế. Hệ thống kết hợp giữa **mô hình đồ thị tác tử (LangGraph)**, **hệ thống quy tắc phân tầng cấp cứu y khoa (Australasian Triage Scale - ATS)** và **bàn làm việc điều phối thực tế cho nhân viên y tế (HITL Workbench)**.

### Mục tiêu giải quyết:

1. **An toàn người bệnh là trên hết (Clinical Safety First):** Tự động phát hiện các ca tối khẩn (Acute STEMI, Đột quỵ, Sốc phản vệ, Suy hô hấp cấp) qua **Zero-Token Emergency Gate** dựa trên quy tắc trước khi gọi LLM và đưa ra hướng dẫn cấp cứu 115.
2. **Phân luồng chuyên khoa chính xác:** Định tuyến bệnh nhân đúng cơ sở y tế gần nhất (VD: Vinmec Riverside Long Biên, Vinmec Times City, Vinmec Central Park...) và đúng chuyên khoa phù hợp với triệu chứng.
3. **Tiếp nhận đặt lịch qua hội thoại (Conversational Booking Intake):** Tự nhiên trích xuất tên, số điện thoại, ngày khám tương đối ("sáng thứ 2 tuần sau"), tạo mã phiếu hẹn `YC-XXXXXX` trực tiếp vào hệ thống quản lý.
4. **Hỗ trợ điều phối viên can thiệp trực tiếp (Human-in-the-Loop):** Nhân viên y tế có thể theo dõi live phiên chat của bệnh nhân và chủ động tiếp quản (takeover) xử lý các ca phức tạp hoặc ca cần xác nhận lịch đặc biệt.

---

## 2. Các tính năng cốt lõi

* **Phiếu đăng ký trên chatbot:**
  * Kiểm tra họ tên, số di động Việt Nam, ngày sinh, ngày khám và thông tin người giám hộ khi bệnh nhân dưới 18 tuổi.
  * Ngày khám phải hợp lệ và nằm từ hôm nay đến tối đa 90 ngày tới (khoảng 3 tháng), theo múi giờ Việt Nam.
  * Yêu cầu xác nhận đồng ý trước khi gửi; kiểm tra lại dữ liệu ở backend.
  * Giữ các trường người dùng đã sửa khi AI cập nhật dữ liệu; lấy ID cơ sở từ catalog.

* **Hybrid RAG:** Kết hợp tìm kiếm vector ChromaDB với SQLite FTS5. PostgreSQL/Supabase lưu dữ liệu nghiệp vụ; ChromaDB lưu các đoạn tài liệu và embedding phục vụ truy xuất.

* **🚨 Cổng phân tầng cấp cứu Zero-Token (ATS Level 1-5):**
  * Tách biệt hoàn toàn các triệu chứng đe dọa tính mạng (đau ngực dữ dội, vã mồ hôi, khó thở, hôn mê, co giật, méo miệng...) ra khỏi luồng xử lý LLM thông thường.
  * Nhánh phản hồi khẩn cấp dựa trên quy tắc đưa ra lộ trình phân tầng (Care Pipeline) và nút gọi cấp cứu khẩn cấp 115.

* **🩺 Hỏi bệnh thích ứng (Adaptive Fact-Aware Probing):**
  * Áp dụng nguyên tắc giao tiếp lâm sàng: Chỉ hỏi từng câu hỏi một, không hỏi dồn dập nhiều câu gây quá tải cho bệnh nhân.
  * Ghi nhớ các sự thật lâm sàng đã thu thập (`clinical_facts`) vào bộ nhớ phiên để không hỏi lặp lại.

* **🌐 Hỗ trợ song ngữ toàn diện (Bilingual Vietnamese & English):**
  * Tự động phát hiện và chuyển đổi ngôn ngữ linh hoạt theo ngôn ngữ bệnh nhân nhập vào.
  * Bản địa hóa toàn bộ hệ thống gợi ý chuyên khoa, cảnh báo an toàn và hướng dẫn điều phối.

* **🧠 Quản lý bộ nhớ hội thoại & Hồ sơ bệnh nhân dài hạn:**
  * **Compaction + SOAP Notes:** Nén hội thoại nhiều lượt thành bản tóm tắt bệnh án chuẩn y khoa SOAP (Subjective, Objective, Assessment, Plan), tối ưu chi phí token và tránh trôi ngữ cảnh.
  * **Cross-Session Memory:** Ghi nhớ sở thích cơ sở khám, tiền sử bệnh và các tác vụ đang chờ xử lý (`open_loops`).

* **📅 Tra cứu bác sĩ & Lịch trống thời gian thực:**
  * Đồng bộ và truy vấn trực tiếp danh sách bác sĩ, chuyên khoa và khung giờ còn trống từ cơ sở dữ liệu Supabase/PostgreSQL.

* **⚡ Failover LLM Gateway có tính sẵn sàng cao (High Availability):**
  * Cơ chế Hedged Requests & Circuit Breaker: Tự động chạy đua giữa nhà cung cấp chính (OpenRouter) và các nhà cung cấp dự phòng (Google Gemini, OpenAI và DeepSeek tùy cấu hình).
  * Tự động cooldown provider gặp sự cố hạn ngạch hoặc lỗi kết nối.

* **📡 Trải nghiệm phản hồi mượt mà qua Server-Sent Events (SSE):**
  * Hỗ trợ streaming câu trả lời từng từ tại `POST /api/v1/chat/stream`.
  * Cơ chế tự phục hồi: Tự động fallback về REST polling `POST /api/v1/chat` nếu môi trường mạng gián đoạn SSE.

---

## 3. Kiến trúc hệ thống & Luồng xử lý

```mermaid
flowchart TD
    Patient([Bệnh nhân / Người dùng]) -->|SSE Stream / REST| API[FastAPI Gateway]
    
    subgraph Core_Backend [Hạ tầng Backend FastAPI]
        API --> Auth[Xác thực JWT & Khách]
        API --> Hist[Lưu trữ lịch sử & Đồng bộ Session]
        API --> WB[Dịch vụ Điều phối Y tế & Lịch hẹn]
    end

    subgraph LangGraph_Agent [LangGraph Multi-Agent Engine]
        API --> LangInit[Khởi tạo AgentState]
        LangInit --> AnalyzeNode[1. Analyze Node & Safety Gate]
        
        AnalyzeNode -->|Cấp cứu ATS 1-2| EmgGate[Zero-Token Emergency Response]
        AnalyzeNode -->|Hỏi thêm triệu chứng| Probing[Fact-Aware Probing]
        AnalyzeNode -->|Đã rõ triệu chứng| CriticNode[2. Clinical Critic / Reflexion]
        
        CriticNode -->|Cần chỉnh sửa| AnalyzeNode
        CriticNode -->|Đã phê duyệt| DocNode[3. Find Doctors & Slots Node]
        
        DocNode --> RespondNode[4. Respond Node & Compaction]
        Probing --> RespondNode
        EmgGate --> RespondNode
    end

    subgraph Data_Services [Tầng dữ liệu & Trí tuệ nhân tạo]
        DocNode -.-> DB[(PostgreSQL / Supabase)]
        RespondNode -.-> RAG[Hybrid RAG: ChromaDB + SQLite FTS5]
        RAG -.-> Vector[(ChromaDB cục bộ)]
        RespondNode -.-> MemSvc[Patient Memory & SOAP Service]
        AnalyzeNode -.-> LLMGateway[Failover LLM Gateway<br/>OpenRouter / Gemini / OpenAI / DeepSeek]
    end

    subgraph Coordination_Workbench [Bàn điều phối viên HITL]
        WB --> StaffApp[Giao diện Điều phối viên Live]
        StaffApp -.->|Tiếp quản ca/Duyệt lịch| Patient
    end
```

---

## 4. Bảng biến môi trường (Environment Variables)

Sao chép `.env.example` thành `.env` tại thư mục gốc và cấu hình các giá trị cần thiết:

```bash
cp .env.example .env
```

| Tên biến | Bắt buộc | Mặc định | Mô tả chi tiết |
|:---|:---:|:---|:---|
| **CẤU HÌNH LLM** | | | |
| `OPENROUTER_API_KEY` | Khuyên dùng | `""` | Khóa API OpenRouter chính (dùng cho mô hình `openai/gpt-4o-mini`). |
| `OPENROUTER_BACKUP_KEYS` | Tùy chọn | `""` | Danh sách khóa OpenRouter dự phòng, cách nhau bằng dấu phẩy. |
| `OPENROUTER_MODEL_NAME` | Tùy chọn | `openai/gpt-4o-mini` | Tên mô hình AI trên OpenRouter. |
| `GOOGLE_AI_API_KEY` | Có khi dùng vector | `""` | Khóa Google AI Studio cho LLM Gemini và tạo embedding bằng `models/gemini-embedding-001`. |
| `GOOGLE_AI_MODEL_NAME` | Tùy chọn | `gemini-3.1-flash-lite` | Tên mô hình hội thoại Gemini; độc lập với mô hình embedding. |
| `DEEPSEEK_API_KEY` | Tùy chọn | `""` | Khóa API khi sử dụng provider DeepSeek. |
| `DEEPSEEK_MODEL_NAME` | Tùy chọn | `DeepSeek-V4.1-Flash` | Tên model trong cấu hình code; cần phù hợp với model tài khoản API có quyền dùng. |
| `OPENAI_API_KEY` | Tùy chọn | `""` | Khóa OpenAI chính thức (nếu sử dụng trực tiếp OpenAI). |
| `LLM_REQUEST_TIMEOUT_SECONDS` | Tùy chọn | `12.0` | Timeout cho từng request LLM đơn lẻ (giây). |
| `LLM_HEDGE_DELAY_SECONDS` | Tùy chọn | `3.0` | Thời gian trễ trước khi kích hoạt provider thứ 2 đua kết quả. |
| `LLM_TOTAL_TIMEOUT_SECONDS` | Tùy chọn | `15.0` | Tổng thời gian tối đa cho toàn bộ lượt gọi LLM. |
| `LLM_FAILURE_COOLDOWN_SECONDS` | Tùy chọn | `30.0` | Thời gian đóng băng tạm thời provider bị lỗi (giây). |
| **CƠ SỞ DỮ LIỆU & LƯU TRỮ** | | | |
| `DATABASE_URL` | **Có** | `""` | Chuỗi kết nối PostgreSQL cho backend, ví dụ `postgresql://user:password@localhost:5432/dbname`. |
| `CHROMA_PERSIST_DIR` | Tùy chọn | `./data/chroma` | Thư mục lưu Vector DB ChromaDB; cần lưu bền vững khi triển khai. |
| `DATABASE_AUTO_CREATE` | Tùy chọn | `true` | Tự động tạo bảng ORM khi khởi động ứng dụng nếu chưa có. |
| `SUPABASE_URL` | Tùy chọn | `""` | URL dự án Supabase (nếu kết nối dữ liệu bác sĩ/dịch vụ). |
| `SUPABASE_KEY` | Tùy chọn | `""` | Anon/Public API Key của Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` | Tùy chọn | `""` | Service Role Key cho quyền truy cập quản trị Supabase. |
| **XÁC THỰC & BẢO MẬT (AUTH)** | | | |
| `JWT_SECRET_KEY` | **Có** | `""` | Khóa bí mật ngẫu nhiên dùng để ký và xác minh JWT; thay giá trị mẫu trong `.env.example`. |
| `AUTH_PROVIDER` | Tùy chọn | `custom` | Cơ chế xác thực: `custom` hoặc `supabase`. |
| `JWT_ALGORITHM` | Tùy chọn | `HS256` | Thuật toán băm JWT. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Tùy chọn | `15` | Thời gian hết hạn của Access Token (phút). |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Tùy chọn | `30` | Thời gian hết hạn của Refresh Token (ngày). |
| `CORS_ORIGINS` | Tùy chọn | `http://localhost:5173` | Danh sách URL frontend được phép gọi API (phân tách bởi dấu phẩy). |

---

## 5. Hướng dẫn cài đặt & Chạy dự án (Setup Instructions)

### Yêu cầu tiên quyết (Prerequisites)

* **Python:** Phiên bản `3.11` trở lên
* **Node.js:** `20.19+` hoặc `22.12+` và `npm` (để chạy frontend Vite 7)
* **Database:** PostgreSQL (hỗ trợ pgvector nếu dùng DB vector) hoặc dự án Supabase đã có dữ liệu bác sĩ, cơ sở và lịch khám
* **Hệ điều hành:** Hỗ trợ Windows, macOS, Linux

---

### Lấy mã nguồn (Clone Repository)

```bash
git clone https://github.com/AI20K-Build-Phase-Cohort-4/P-124.git
cd P-124
```

---

### Bước 1: Khởi tạo & Chạy Backend (FastAPI)

1. **Tạo và kích hoạt môi trường ảo (Virtual Environment):**

   * **Windows (Command Prompt - CMD):**
     ```cmd
     py -3.11 -m venv .venv
     .venv\Scripts\activate.bat
     ```

   * **Windows (PowerShell):**
     ```powershell
     py -3.11 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

   * **macOS / Linux (Bash / Zsh):**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Cài đặt các gói phụ thuộc (Dependencies):**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Thiết lập file biến môi trường (`.env`):**
   * **Windows (CMD):**
     ```cmd
     copy .env.example .env
     ```
   * **Windows (PowerShell):**
     ```powershell
     Copy-Item .env.example .env
     ```
   * **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```
   * *Mở file `.env` vừa tạo và điền các khóa cấu hình chính:*
     * `DATABASE_URL`: Chuỗi kết nối PostgreSQL (ví dụ: `postgresql+psycopg://user:password@localhost:5432/vcare`).
     * `OPENROUTER_API_KEY` (hoặc `GOOGLE_AI_API_KEY` / `OPENAI_API_KEY`): Khóa API cho mô hình ngôn ngữ lớn (LLM).
     * `JWT_SECRET_KEY`: Khóa bí mật dùng để ký và xác thực JWT token.
     * `SUPABASE_URL` và `SUPABASE_KEY`: Thông tin kết nối Supabase (nếu đồng bộ cơ sở y tế/bác sĩ).
     *(Tham khảo chi tiết bảng mô tả đầy đủ các tham số tại [Mục 4: Bảng biến môi trường](#4-bảng-biến-môi-trường-environment-variables)).*

4. **Khởi tạo cơ sở dữ liệu (Tùy chọn):**
   * Mặc định hệ thống tự động sinh cấu trúc bảng ORM khi khởi động (`DATABASE_AUTO_CREATE=true`).
   * Nếu muốn áp dụng thủ công các migration schema qua Alembic:
     ```bash
     alembic upgrade head
     ```

5. **Khởi chạy máy chủ Backend FastAPI:**
   * **Windows (CMD / PowerShell):**
     ```cmd
     python scripts\run_backend.py --host 127.0.0.1 --port 8000
     # Hoặc khởi chạy trực tiếp qua Uvicorn:
     python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
     ```
   * **macOS / Linux:**
     ```bash
     python3 scripts/run_backend.py --host 127.0.0.1 --port 8000
     # Hoặc:
     python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
     ```
   * 📘 **Swagger UI tài liệu API tương tác:** **<http://127.0.0.1:8000/docs>**
   * 🩺 **Kiểm tra trạng thái sẵn sàng (Health Check):** **<http://127.0.0.1:8000/health/ready>**

---

### Bước 2: Khởi tạo & Chạy Frontend (React 19 + Vite)

Mở một cửa sổ Terminal mới tại thư mục gốc của dự án `P-124`:

1. **Di chuyển vào thư mục frontend & cài đặt thư viện:**
   * **Windows (CMD / PowerShell):**
     ```cmd
     cd frontend
     npm install
     ```
   * **macOS / Linux:**
     ```bash
     cd frontend
     npm install
     ```

2. **Khởi chạy Frontend ở chế độ phát triển (Dev Mode):**
   ```bash
   npm run dev
   ```
   * 🌐 Giao diện ứng dụng web sẽ hoạt động tại: **<http://localhost:5173>**
   * Frontend đã tích hợp sẵn proxy tự động chuyển tiếp toàn bộ truy vấn `/api/` sang Backend tại `http://localhost:8000`.

---

### Bước 3: Tạo & Đồng bộ Vector DB ChromaDB (Tùy chọn)

Dự án ứng dụng kiến trúc **Hybrid RAG** (kết hợp vector search ChromaDB và SQLite FTS5 full-text search). Chỉ mục vector mẫu đã được lưu trữ sẵn tại thư mục `data/chroma/`.

Nếu bạn muốn tạo lại hoặc cập nhật chỉ mục vector embedding từ nguồn dữ liệu JSONL của Vinmec (`data/datalake/rag/specialties.jsonl`):
* **Windows (CMD / PowerShell):**
  ```cmd
  python scripts\build_vector_store.py
  ```
* **macOS / Linux:**
  ```bash
  python3 scripts/build_vector_store.py
  ```

> **Lưu ý:** Script sử dụng Gemini Embedding API (`GOOGLE_AI_API_KEY`). Nếu vector store chưa khởi tạo hoặc chưa có API key, hệ thống sẽ tự động fallback sang nhánh tìm kiếm SQLite FTS5 để đảm bảo ứng dụng luôn hoạt động thông suốt.

---

### Bước 4: Khởi chạy nhanh toàn bộ qua Docker (Tùy chọn)

Nếu bạn đã cài đặt Docker và Docker Compose trên hệ thống:
```bash
docker compose up --build
```
Compose sẽ tự động xây dựng container cho Backend FastAPI và container PostgreSQL hỗ trợ pgvector.

---

### Danh mục các phân hệ & Trang chức năng trên Web

| Phân hệ / URL | Người dùng | Chức năng chính |
|:---|:---|:---|
| `/` | Bệnh nhân | Chatbot tiếp đón thông minh, sàng lọc triệu chứng, phân tầng ATS & phân luồng chuyên khoa |
| `/booking` | Bệnh nhân | Phiếu đăng ký đặt lịch khám, chọn cơ sở y tế Vinmec, chọn ngày khám và bác sĩ |
| `/staff/queue` | Điều phối viên | Quản lý hàng đợi tiếp nhận bệnh nhân, lập phương án khám, xếp lịch & xử lý cọc |
| `/staff/chat` | Điều phối viên | Khung tin nhắn thời gian thực, nhận ca, tiếp quản (takeover) từ AI để tư vấn trực tiếp |
| `/staff/emergency` | Đội ngũ cấp cứu | Theo dõi và tiếp nhận tức thì các ca có cờ đỏ cấp cứu tối khẩn (ATS Level 1-2) |
| `/family` | Bệnh nhân | Quản lý hồ sơ y bạ gia đình & người phụ thuộc |
| `/docs` | Lập trình viên / Đánh giá | Tài liệu tương tác API Swagger UI đầy đủ |

---

## 6. Kịch bản & Câu hỏi mẫu (Sample Queries)

Trợ lý y tế P-124 được thiết kế đặc thù cho các tình huống tiếp đón và sàng lọc lâm sàng thực tế. Dưới đây là các nhóm câu hỏi thử nghiệm tiêu biểu:

### Kịch bản 1: Cảnh báo cấp cứu khẩn cấp (Zero-Token Emergency Gate - ATS 1)

* **Câu hỏi bệnh nhân:**
  > *"Bệnh nhân bị đau thắt ngực dữ dội, vã mồ hôi và khó thở cấp tính"*
* **Hành vi hệ thống:**
  * **0 Token LLM:** Cơ chế Regex & Clinical Lexicon ngắt ngay lập tức, không tốn thời gian gọi mô hình AI.
  * **Kết quả:** Phân loại `ATS Level 1`, hiển thị cảnh báo đỏ và lộ trình cấp cứu: Ưu tiên tối thượng gọi ngay **115** hoặc tới thẳng phòng Cấp cứu gần nhất, không chờ xếp lịch.

---

### Kịch bản 2: Hỏi bệnh đau khớp & Phân luồng cơ sở Long Biên (ATS 4-5)

* **Câu hỏi bệnh nhân:**
  > *"Chào bạn, tôi đang bị đau khớp ở đầu gối chân phải, hiện tại tôi đang gặp vấn đề về đi lại thì không biết có bệnh viện nào ở gần khu vực Long Biên - Hà Nội để tôi có thể đi khám không?"*
* **Hành vi hệ thống:**
  * Nhận diện vị trí địa lý **Quận Long Biên** $\rightarrow$ Gợi ý ngay **Bệnh viện Đa khoa Quốc tế Vinmec Riverside** (Lô H1-YT, Phúc Lợi, Long Biên).
  * Định tuyến đúng chuyên khoa: **Chấn thương chỉnh hình & Cột sống**.
  * Hỏi làm rõ (Probing): Đặt 1 câu hỏi trọng tâm về thời gian xuất hiện cơn đau hoặc tiền sử chấn thương để chuẩn bị bệnh án.

---

### Kịch bản 3: Tra cứu bác sĩ & Khung giờ khám thực tế

* **Câu hỏi bệnh nhân:**
  > *"Tôi muốn tìm bác sĩ chuyên khoa Cơ xương khớp hoặc Chấn thương chỉnh hình có lịch khám vào sáng thứ 7 tuần này ở Vinmec Times City"*
* **Hành vi hệ thống:**
  * Trích xuất cơ sở `Vinmec Times City`, chuyên khoa, thời gian `sáng thứ 7`.
  * Truy vấn cơ sở dữ liệu hiển thị thẻ thông tin bác sĩ thực tế kèm học vị (Tiến sĩ, Thạc sĩ, BSCKII) và các khung giờ còn trống để bệnh nhân lựa chọn.

---

### Kịch bản 4: Đặt lịch khám qua trò chuyện tự nhiên (Conversational Booking)

* **Câu hỏi bệnh nhân:**
  > *"Tôi muốn đăng ký khám khớp gối ở Vinmec Riverside vào sáng thứ 2 tuần sau cho Nguyễn Văn An, số điện thoại 0912345678"*
* **Hành vi hệ thống:**
  * Trích xuất tự động các thực thể: Họ tên, SĐT, ngày tương đối (`thứ 2 tuần sau` chuyển thành ngày chuẩn ISO), buổi sáng, cơ sở.
  * Tự động tạo hồ sơ tiếp nhận trên hệ thống điều phối với mã tiếp nhận định dạng `YC-XXXXXX` (VD: `YC-2449D668`).
  * Đồng bộ thông tin phiếu hẹn sang mục **Tiến trình lịch hẹn** trên giao diện bệnh nhân.

---

### Kịch bản 5: Hủy lịch hẹn khám đã đặt

* **Câu hỏi bệnh nhân:**
  > *"Tôi bận việc đột xuất nên muốn hủy lịch hẹn khám mã YC-2449D668"*
* **Hành vi hệ thống:**
  * Xác nhận thông tin và chuyển trạng thái ca sang `cancelled` (không xóa dữ liệu để phục vụ kiểm toán y tế), giải phóng slot khám cho bệnh nhân khác.

---

### Kịch bản 6: Khám bệnh đa ngữ (English Medical Triage)

* **Câu hỏi bệnh nhân:**
  > *"I have had a severe throbbing headache on my right temple for 3 days with nausea and light sensitivity."*
* **Hành vi hệ thống:**
  * Nhận diện ngôn ngữ tiếng Anh (`en`).
  * Phân tầng hướng về **Neurology Department** (Khoa Thần kinh), đưa ra khuyến cáo theo dõi dấu hiệu thần kinh khu trú hoàn toàn bằng tiếng Anh.

---

## 7. Danh mục API Endpoints

### 1. Trợ lý AI & Hội thoại (`/api/v1/chat`)

| Phương thức | Đường dẫn | Quyền hạn | Mô tả chức năng |
|:---:|:---|:---:|:---|
| `POST` | `/api/v1/chat/stream` | Công khai / User | Gửi tin nhắn và nhận phản hồi trực tiếp dạng SSE streaming. |
| `POST` | `/api/v1/chat` | Công khai / User | Endpoint chat dạng REST truyền thống (dùng khi client không hỗ trợ SSE). |
| `GET` | `/api/v1/chat/conversations` | Người dùng | Lấy danh sách các phiên trò chuyện của người dùng đăng nhập. |
| `GET` | `/api/v1/chat/conversations/{session_id}` | Người dùng | Tải lại toàn bộ lịch sử tin nhắn của một phiên. |
| `DELETE` | `/api/v1/chat/conversations/{session_id}` | Người dùng | Xóa lịch sử phiên hội thoại. |

### 2. Quản lý Đặt lịch khám (`/api/v1/bookings`)

| Phương thức | Đường dẫn | Quyền hạn | Mô tả chức năng |
|:---:|:---|:---:|:---|
| `GET` | `/api/v1/bookings` | Bệnh nhân | Lấy danh sách lịch hẹn cá nhân (cả đặt lịch trực tiếp & qua AI chat). |
| `POST` | `/api/v1/bookings` | Bệnh nhân | Tạo yêu cầu đặt lịch hẹn mới theo khung giờ cụ thể. |
| `POST` | `/api/v1/bookings/hold` | Bệnh nhân | Giữ chỗ tạm thời cho khung giờ khám. |
| `POST` | `/api/v1/bookings/{id}/cancel` | Bệnh nhân / Staff | Hủy lịch hẹn khám, chuyển trạng thái sang đã hủy kèm lý do. |

### 3. Bàn làm việc Điều phối viên (`/api/v1/staff/workbench`)

| Phương thức | Đường dẫn | Mô tả chức năng |
|:---:|:---|:---|
| `GET` | `/api/v1/staff/workbench/cases` | Danh sách ca; `conversations=true` lọc các ca nguồn hội thoại. |
| `GET` | `/api/v1/staff/workbench/cases/{id}` | Chi tiết ca và tin nhắn. |
| `POST` | `/api/v1/staff/workbench/cases/{id}/actions` | Nhận ca, tiếp quản, trả về AI và các thao tác điều phối qua trường `action`. |
| `POST` | `/api/v1/staff/workbench/cases/{id}/messages` | Gửi tin nhắn khi nhân viên có quyền xử lý hội thoại. |
| `PUT` | `/api/v1/staff/workbench/cases/{id}/plan` | Cập nhật phương án khám. |
| `POST` | `/api/v1/staff/workbench/duty/start` | Bắt đầu ca trực. |

Các endpoint này yêu cầu xác thực và quyền nhân viên điều phối. Xem `/docs` của backend
đang chạy để biết đầy đủ schema, thao tác và endpoint.

### 4. Hệ thống & Giám sát (`/health`)

| Phương thức | Đường dẫn | Quyền hạn | Mô tả chức năng |
|:---:|:---|:---:|:---|
| `GET` | `/health` | Công khai | Kiểm tra máy chủ có đang phản hồi (Liveness check). |
| `GET` | `/health/ready` | Công khai | Kiểm tra kết nối cơ sở dữ liệu PostgreSQL (Readiness check). |

---

## 8. Kiểm thử & Đảm bảo chất lượng (Testing)

Các bộ kiểm thử bao gồm logic trợ lý, validation phiếu, phân quyền API và điều phối. Một số kiểm thử RAG cần dữ liệu hoặc khóa API đã cấu hình:

```bash
# 1. Chạy toàn bộ test suite của Medical Assistant

pytest tests/test_medical_assistant/ -v

# 2. Kiểm thử riêng các ca cấp cứu và an toàn lâm sàng

pytest tests/test_medical_assistant/test_emergency_safety_v3.py -v

# 3. Kiểm thử luồng hội thoại đặt lịch tự nhiên

pytest tests/test_medical_assistant/test_relative_date_and_booking_summary.py -v

# 4. Kiểm thử API hủy lịch và đặt chỗ

pytest tests/test_booking/test_api.py -v

# 5. Kiểm thử phiếu đăng ký, phân quyền và hồi quy điều phối

python -m pytest tests/test_api/test_chat_booking_validation.py tests/test_api/test_staff_patient_profile_access.py tests/test_coordinator_regressions.py -q

# 6. Kiểm thử logic frontend điều phối (từ thư mục gốc)

node --test tests/coordinator_frontend.test.cjs tests/coordinator_ui.test.cjs

# 7. Kiểm tra định dạng code với Ruff

ruff check .
```

---

Kiểm tra build frontend:

```bash
cd frontend
npm run build
```

## 9. Cấu trúc thư mục dự án

Hệ thống được tổ chức theo chuẩn kiến trúc **Production-Grade AI Agent** phục vụ triển khai thực tế và đáp ứng tiêu chuẩn thẩm định của AI20K:

```text
P-124/
├── alembic/                                 # Database Schema Migrations (Alembic + SQLAlchemy)
│   ├── env.py                               # Cấu hình môi trường migration kết nối PostgreSQL
│   └── versions/                            # 17 migration scripts (Auth, Booking, Workbench, Roles...)
├── configs/                                 # Cấu hình chính sách & Quy tắc điều hành Agent (Control Plane)
│   └── control_plane/                       # Dynamic Clinical Policies (CLINICAL_SOUL.md, PROTOCOLS.md...)
├── src/                                     # Toàn bộ mã nguồn Backend
│   ├── agents/                              # LangGraph Multi-Agent Core
│   │   ├── graph.py                         # State graph (nodes, edges, Reflexion loop, checkpointer)
│   │   ├── state.py                         # AgentState schema trung tâm (TypedDict toàn diện)
│   │   ├── nodes/                           # Các node chức năng chuyên sâu
│   │   │   ├── analyze_node.py              # Phân tích triệu chứng, an toàn & intent
│   │   │   ├── critic_node.py               # Phản biện lâm sàng (Reflexion & Safety verification)
│   │   │   ├── doctor_node.py               # Truy vấn danh sách bác sĩ & khung giờ khám
│   │   │   ├── respond_node.py              # Tạo phản hồi, SOAP notes & nén bộ nhớ
│   │   │   └── helpers.py                   # Tiện ích trích xuất thực thể & địa điểm
│   │   └── tools/                           # Bộ công cụ Agent (@tool)
│   │       ├── medical_tools.py             # Tính toán BMI, phát hiện cờ đỏ cấp cứu ATS 1-2
│   │       └── example_tool.py              # Tra cứu tri thức & tính toán biểu thức an toàn
│   ├── api/                                 # Lớp FastAPI Routers & Endpoints
│   │   ├── routes.py                        # Entry point router trung tâm (/chat, /status)
│   │   ├── endpoints/                       # Các domain REST API chuyên biệt
│   │   │   ├── auth.py                      # Xác thực Supabase JWT, cookie session & RBAC
│   │   │   ├── patient_profiles.py          # Hồ sơ y tế bệnh nhân & tài khoản gia đình
│   │   │   ├── booking.py                   # Tiếp nhận, kiểm tra & hủy lịch hẹn
│   │   │   ├── coordination.py              # Điều phối phân tầng ca khám & cấp cứu
│   │   │   ├── workbench.py                 # HITL Coordinator Workbench & tiếp quản ca
│   │   │   ├── package.py                   # Đăng ký gói khám sức khỏe Vinmec
│   │   │   ├── catalog.py                   # Danh mục cơ sở y tế, chuyên khoa, dịch vụ
│   │   │   ├── notification.py              # Thông báo đẩy & lịch hẹn
│   │   │   └── zalo.py                      # Webhook tích hợp Zalo OA Mini App
│   │   ├── dependencies.py                  # Dependencies xác thực và kiểm soát quyền
│   │   └── handlers.py                      # Global exception & error handlers
│   ├── models/                              # Dữ liệu ORM & Schemas
│   │   ├── schemas.py                       # Pydantic schemas hub trung tâm (ChatRequest/Response...)
│   │   └── tables.py                        # SQLAlchemy ORM Models (User, Booking, PatientProfile...)
│   ├── services/                            # Tầng Business Logic & Dịch vụ ngoài
│   │   ├── llm.py                           # HA Failover LLM Gateway (Circuit Breaker, Hedged Requests)
│   │   ├── auth.py & supabase_auth.py       # Quản lý định danh người dùng & RBAC
│   │   ├── booking.py                       # Xử lý giữ chỗ & giải phóng slot hết hạn
│   │   ├── patient_profiles.py              # Quản lý hồ sơ y bạ gia đình
│   │   └── workbench.py                     # Quản lý hàng đợi & bàn trực điều phối
│   ├── db/                                  # Database connection pool & session factory
│   ├── schemas/                             # Chi tiết Pydantic validation schemas theo domain
│   ├── medical_assistant/                   # Domain core & RAG retrieval engine
│   │   ├── domain/                          # Nghiệp vụ y khoa (ATS Triage, Fact-aware probing)
│   │   ├── rag/                             # Vector Store ChromaDB & Store Cache
│   │   └── ingestion/                       # Pipeline crawl dữ liệu Vinmec & xử lý RAG
│   ├── config.py                            # Pydantic Settings (Quản lý biến môi trường)
│   └── main.py                              # FastAPI Application Entry Point
├── frontend/                                # Ứng dụng Web giao diện người dùng (React 19 + Vite)
│   ├── src/
│   │   ├── features/                        # Modules tính năng chính (Chat, Booking, Workbench, Profiles)
│   │   ├── pages/                           # Các trang ứng dụng (Login, Patient, Coordinator, Family)
│   │   └── App.tsx                          # Router & cấu hình giao diện
│   └── vite.config.ts
├── tests/                                   # Pytest test suite toàn diện
│   ├── test_agents/                         # Kiểm thử LangGraph Agent flow & State structure
│   ├── test_api/                            # Kiểm thử REST API, auth, cookies & validation
│   └── test_medical_assistant/              # Kiểm thử kịch bản lâm sàng, cấp cứu, nén SOAP & RAG
├── scripts/                                 # Scripts vận hành, tiện ích & khởi chạy hệ thống
│   ├── run_backend.py                       # Launcher máy chủ Backend FastAPI (tương thích Windows/Linux)
│   ├── build_vector_store.py                # Xây dựng chỉ mục vector ChromaDB từ dữ liệu tri thức RAG
│   ├── verify_logins.py                     # Kiểm thử đăng nhập Supabase Auth & RBAC
│   ├── link_doctors_to_facilities.py        # Liên kết danh mục bác sĩ với cơ sở bệnh viện Vinmec
│   └── seed_full_database.py                # Nạp dữ liệu mẫu ban đầu cho cơ sở dữ liệu
├── docs/                                    # Tài liệu kỹ thuật
│   ├── guide/                               # Technical Guidebook 10 chương chuyên sâu
│   └── architecture_diagram.md              # Sơ đồ kiến trúc Mermaid
├── eval/                                    # Bộ công cụ đánh giá & Benchmark
│   ├── results/                             # Kết quả benchmark chi tiết (JSON) & report.md
│   ├── run_realistic_benchmark.py           # Benchmark 10 ca lâm sàng thực tế
│   ├── run_multi_specialty_pipeline_benchmark.py # Benchmark 20 ca phân luồng chuyên khoa
│   └── README.md                            # Hướng dẫn và tiêu chí đánh giá KPI
├── presentation/                            # Tài liệu thuyết trình Demo Day
│   └── README.md                            # Cấu trúc Pitch Deck 10 slides & Video demo checklist
├── .github/                                 # Cấu hình GitHub & CI/CD
│   ├── workflows/ci.yml                     # Pipeline CI tự động (Lint, Pytest, Docker Build)
│   └── hooks/                               # Hooks đồng bộ mã nguồn
├── .agents/                                 # Cấu hình Agentic workflows & tool rules
├── Dockerfile                               # Multi-stage production container build
├── docker-compose.yml                       # Docker Compose chạy Backend + PostgreSQL/pgvector
├── README_boilerplate.md                    # Khung README mẫu tiêu chuẩn của chương trình
├── .env.example                             # Mẫu biến môi trường
└── requirements.txt                         # Danh mục thư viện Python
```

---

## 10. Đóng góp & Bản quyền

Dự án được phát triển theo tiêu chuẩn giáo dục và ứng dụng thực tiễn của chương trình **VinUni AI20K Build Phase**.
Mọi đóng góp, báo cáo lỗi và đề xuất vui lòng tuân thủ theo tài liệu [CONTRIBUTING.md](CONTRIBUTING.md) và [SECURITY.md](SECURITY.md).

**Giấy phép bản quyền:** [MIT License](LICENSE) — Được phép sử dụng và mở rộng cho mục đích giáo dục và nghiên cứu khoa học y tế.
