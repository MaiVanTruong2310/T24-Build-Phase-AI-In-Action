# Architecture Diagram

## System Overview

```mermaid
graph TB
    OBS[Observability<br/>Prometheus·Grafana·Loki·Tempo]
    AIOBS[AI Observability<br/>Langfuse]

    User([Bệnh nhân/Điều phối viên]) --> UI[Frontend<br/>Patient App / Staff Dashboard]
    UI -->|REST API / WebSocket| API[FastAPI Backend]
    API --> DB[(PostgreSQL·Redis·Kafka)]
    API -->|REST API| Agent[LangGraph Agent]
    Agent --> LLM[LLM Service]
    Agent --> Tools[Agent Tools]
    Tools -->|REST API| API
    Agent --> VS[(pgvector<br/>Vector Store)]

    API -.-> OBS
    Agent -.-> AIOBS
```

## Agent Flow

```mermaid
graph LR
    Start([Tin nhắn]) --> Intent[Intent]
    Intent --> Safety{Safety}
    Safety -->|Khẩn cấp| Emg[Emergency Alert]
    Safety -->|An toàn| RAG[RAG Retrieval]
    RAG --> Reason[Reasoning]
    Reason --> Conf{Confidence}
    Conf -->|Cao| High[Suggest + Tools]
    Conf -->|Thấp| Low[Handoff HITL]
    Emg --> Staff[Staff Dashboard]
    Low --> Staff
    High --> Reply([Phản hồi])
    Staff --> Reply
```

## Component Details

| Component        | Technology                    | Purpose                                                                                 |
| ---------------- | ----------------------------- | --------------------------------------------------------------------------------------- |
| Frontend         | React (Vercel)                | Giao diện Patient App & Staff Dashboard                                                 |
| Backend          | FastAPI                       | Lớp duy nhất ghi dữ liệu, thực thi nghiệp vụ (Auth, Appointment, HITL, Notification...) |
| Agent            | LangGraph                     | Điều phối luồng tư vấn AI (Intent, Safety, RAG, Reasoning, Confidence)                  |
| LLM              | OpenAI/Gemini                 | Language model cho Agent (Intent Detection, Reasoning)                                  |
| Database         | PostgreSQL                    | Data persistence + cache (Redis) + message queue (Kafka)                                |
| Vector Store     | pgvector                      | RAG / embeddings, chỉ dùng riêng cho Agent                                              |
| Observability    | Prometheus·Grafana·Loki·Tempo | Metrics, logs, traces cho Backend                                                       |
| AI Observability | Langfuse                      | Theo dõi reasoning, tool calls, confidence của Agent                                    |
