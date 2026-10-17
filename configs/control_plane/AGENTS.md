# Multi-Agent Coordination Specification (P-124 Control Plane)

## 1. Phân Tầng Trách Nhiệm Các Agent

### 1.1 Triage & Analyze Agent (`analyze_node`)
- **Nhiệm vụ:**
  - Tiếp nhận input người dùng, phân tích an ninh (Hook 1: Security Gateway).
  - Phân loại mức độ khẩn cấp (ATS Level 1–5, Urgency Tier).
  - Bóc tách thực thể đặt khám (Họ tên, SĐT, ngày giờ, cơ sở, chuyên khoa).
  - Trích xuất thông tin lâm sàng (Subjective/Objective facts).
- **Ranh giới:** Không tự động sinh văn bản hoàn chỉnh gửi người dùng trước khi qua Critic.

### 1.2 Clinical Critic Agent (`critic_node`)
- **Nhiệm vụ:**
  - Kiểm định độc lập theo phương pháp Reflexion (Shinn et al., 2023).
  - Đánh giá 5 Rubric y khoa: Ưu tiên giải phẫu sinh tồn, phân tầng rủi ro, phát hiện dấu hiệu cấp cứu đỏ.
  - Phát lệnh `REVISE` khi phát hiện bỏ sót nguy cơ, hoặc `PASS` để chuyển tiếp.

### 1.3 Scheduling & Doctor Agent (`doctor_node`)
- **Nhiệm vụ:**
  - Tra cứu bác sĩ cơ hữu tại cơ sở được chọn theo chuyên khoa đích.
  - Tìm kiếm ca khám còn trống trong khoảng thời gian người bệnh yêu cầu.

### 1.4 Response & UI Formatter Agent (`respond_node`)
- **Nhiệm vụ:**
  - Định dạng câu trả lời theo đúng Clinical Soul.
  - Tích hợp Live Booking Panel snapshot, danh sách bác sĩ, và Quick Replies.
  - Gắn Medical Disclaimer bắt buộc vào cuối tin nhắn.

### 1.5 Human Coordinator Agent (Workbench)
- **Nhiệm vụ:**
  - Giám sát luồng đặt khám theo thời gian thực (Live WebSocket).
  - Can thiệp duyệt giữ chỗ, chuyển khoa hoặc điều phối liên khoa khi ca bệnh phức tạp.
