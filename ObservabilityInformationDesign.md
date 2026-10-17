# Thiết kế Grafana Dashboard với Prometheus, Loki, Tempo

## 1. Nguyên tắc bố cục

Sắp xếp dashboard từ tổng quan đến chi tiết: **Overview → Service → Dependency/Infra → Logs → Traces**. Nên có các biến (variables) ở trên cùng: `env`, `service`, `instance`, `tenant` (nếu multi-tenant) và time range.

## 2. Các mục cần có

### Row 1: Overview (Prometheus), nhìn 5 giây biết hệ thống ổn hay không

| Panel              | Thông số                         |
| ------------------ | -------------------------------- |
| Request rate (RPS) | Tổng và theo service             |
| Error rate (%)     | 5xx / tổng request               |
| Latency            | p50 / p95 / p99                  |
| Service up/down    | Trạng thái `up` của từng service |
| Alert đang firing  | Số alert theo mức độ             |
| Saturation         | CPU, RAM tổng quan               |

Dùng Stat/Gauge cho các số này, màu đỏ/vàng/xanh theo ngưỡng.

### Row 2: Application / RED metrics theo từng service (Prometheus)

- **Rate**: RPS theo endpoint, method
- **Errors**: tỉ lệ 4xx, 5xx theo endpoint; top endpoint lỗi
- **Duration**: histogram p95/p99 theo endpoint, top endpoint chậm nhất
- **In-flight requests** (request đang xử lý)

```promql
# RPS
sum(rate(http_server_requests_seconds_count{service="$service"}[5m])) by (uri)

# Error rate
sum(rate(http_server_requests_seconds_count{service="$service",status=~"5.."}[5m]))
/ sum(rate(http_server_requests_seconds_count{service="$service"}[5m]))

# p95
histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{service="$service"}[5m])) by (le, uri))
```

### Row 3: Runtime (Prometheus)

**Spring Boot (Micrometer/Actuator):**

- JVM heap/non-heap used vs max, GC pause time và GC count
- Thread: live, daemon, peak, blocked
- Tomcat threads busy/max, connections
- **HikariCP**: active/idle/pending connections, connection acquire time, timeouts
- CPU process, uptime, file descriptors

**FastAPI (prometheus-fastapi-instrumentator / prometheus_client):**

- Request/latency theo handler
- Process CPU/memory, số worker, open FDs
- Python GC, asyncio task/event-loop lag (nếu có)

### Row 4: Infrastructure (Prometheus, node-exporter / cAdvisor / kube-state-metrics)

- CPU, memory, disk usage và I/O, network in/out
- Container/Pod: CPU throttling, OOMKilled, restart count, pod status
- Disk gần đầy (dự báo bằng `predict_linear`)

### Row 5: Dependencies (Prometheus)

- **Database**: query time, số connection, slow query, deadlock (postgres_exporter / mysqld_exporter)
- **Redis**: hit rate, memory, evicted keys, connected clients
- **Message queue (Kafka/RabbitMQ)**: consumer lag, queue depth, publish/consume rate
- **Gọi API ngoài** (LLM, payment, SMS...): latency, error rate, timeout, retry

### Row 6: Business metrics (Prometheus, custom metrics)

Với chatbot platform, nên có thêm:

- Số tin nhắn/phút, số conversation đang active
- Latency của LLM (time to first token, tổng thời gian), token usage (input/output)
- Tỉ lệ fallback / không trả lời được, tỉ lệ lỗi LLM
- Chi tiêu theo tenant, theo gói dịch vụ (cẩn thận cardinality của label `tenant`)

### Row 7: Logs (Loki)

| Panel                 | Nội dung                                           |
| --------------------- | -------------------------------------------------- |
| Log volume theo level | Biểu đồ cột INFO/WARN/ERROR theo thời gian         |
| Error rate từ log     | Số dòng ERROR/phút theo service                    |
| Top error messages    | Bảng các lỗi lặp nhiều nhất                        |
| Log stream            | Logs panel, lọc theo `service`, `level`, `traceId` |

```logql
# Log volume theo level
sum by (level) (count_over_time({service="$service"} | json [1m]))

# Lỗi
{service="$service"} |= "ERROR" | json | line_format "{{.message}}"

# Top lỗi
topk(10, sum by (message) (count_over_time({service="$service"} | json | level="ERROR" [1h])))
```

Log nên ở dạng **JSON có trường `traceId`, `spanId`, `level`, `service`, `tenant`** để liên kết với Tempo.

### Row 8: Traces (Tempo)

- **Service Graph / Node Graph**: quan hệ giữa các service, request rate, error rate, latency trên mỗi cạnh (cần bật metrics-generator của Tempo)
- **Trace search table**: lọc theo service, duration > X ms, status = error
- **Slow traces**: top trace chậm nhất
- **Span metrics**: duration theo span name, tỉ lệ lỗi theo span
- **Trace detail view**: waterfall, xem span nào chiếm thời gian (DB query, gọi LLM, HTTP ngoài...)

### Row 9: Alerts / SLO

- SLI/SLO: availability (%) và latency target, error budget còn lại, burn rate
- Danh sách alert đang firing

## 3. Liên kết 3 nguồn (phần quan trọng nhất)

| Hướng           | Cách cấu hình                                                                                         |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| Metrics → Trace | Bật **Exemplars** trong Prometheus, gắn `trace_id` vào histogram, cấu hình exemplar trong data source |
| Log → Trace     | Data source Loki dùng **Derived fields** để regex `traceId` thành link sang Tempo                     |
| Trace → Logs    | Data source Tempo dùng **Trace to logs**, map theo `service.name` và `traceId`                        |
| Trace → Metrics | **Trace to metrics** cho các query RED của service đó                                                 |

Quy trình debug: thấy spike latency ở panel → bấm exemplar → mở trace → thấy span chậm → xem log của đúng trace đó.

## 4. Gợi ý tổ chức dashboard

Thay vì dồn tất cả vào một dashboard, nên chia:

1. **Overview**: tổng quan toàn hệ thống
2. **Service detail** (dùng biến `$service`): RED, runtime, logs, traces của một service
3. **Infrastructure / Kubernetes**
4. **Dependencies** (DB, Redis, MQ)
5. **Business / LLM**

Dùng data link giữa các dashboard (từ Overview bấm vào service để sang Service detail).

## 5. Lưu ý thực tế

- Tránh label có cardinality cao (`user_id`, `conversation_id`, `uri` chứa ID) trong Prometheus; để chúng trong log/trace.
- Đặt tên service nhất quán giữa metrics, logs, traces (`service.name`).
- Dùng dashboard JSON provisioning và lưu trong Git.
- Có thể import dashboard mẫu trước rồi chỉnh: **4701** (JVM Micrometer), **12900** (Spring Boot), **1860** (Node Exporter).
