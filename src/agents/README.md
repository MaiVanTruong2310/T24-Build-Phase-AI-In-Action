# [DEPRECATED] Legacy Agent Scaffold (`src/agents/`)

> **Cảnh báo (Deprecation Notice):**
> Thư mục `src/agents/` là mã nguồn prototype ban đầu (scaffold boilerplate). 
> Hệ thống production chính thức của Trợ lý Y tế P-124 hiện tại được đặt tại:
> **`src/medical_assistant/agent/`**

---

### Kiến trúc hiện tại của P-124:
- **Production Graph:** `src.medical_assistant.agent.graph.agent`
  - Đầy đủ các nodes: `route_intent_node`, `analyze_node`, `critic_node`, `find_doctors_node`, `info_agent_node`, `respond_node`.
  - Hỗ trợ Reflexion feedback loop, Human-in-the-loop (HITL) intake, và RAG grounded tools.
  - Failover Chat Model với bộ ngắt mạch mạch vòng (circuit breaker) đa nhà cung cấp.

- **Thư mục này (`src/agents/`):**
  - Được giữ lại để tương thích ngược với các bài kiểm thử cơ bản (`tests/test_agents/test_graph.py`).
  - Không được dùng trong API production runtime (`src/main.py` chỉ mount `src.medical_assistant.api.routes`).
