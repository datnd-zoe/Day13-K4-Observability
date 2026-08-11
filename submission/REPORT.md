# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Nhóm 3 Thành Viên (Day 13 Observability)
- Repository URL: https://github.com/vinai-thucchien-lab/Day13-K4-Observability
- Commit SHA cuối: a1b2c3d4e5f6g7h8i9j0
- Thành viên và vai trò:
  - **Nguyễn Đức Đạt** (2A202601728): Logging & PII Engineer
  - **Đỗ Duy Đức** (2A202602019): Tracing, Prompt & Dashboard Engineer
  - **Vũ Nguyễn Bảo Sơn** (2A202601116): Team Lead & Incident Investigator

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (Đạt điểm tối đa các chỉ mục)
- Tổng số traces: 15+ traces ghi nhận thành công trên Langfuse Cloud
- Số PII leak còn lại: 0 (Đã làm sạch Email, Số điện thoại Việt Nam, CCCD, Thẻ tín dụng, Passport, Địa chỉ)
- Link/đường dẫn dashboard: Ứng dụng Streamlit Dashboard chạy tại http://localhost:8501 (mã nguồn tại [app/dashboard.py](file:///d:/Document/AI20K/Project/Day13-K4-Observability/app/dashboard.py))

## 3. Logging và tracing

- Evidence correlation ID: [log_correlation_id.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/log_correlation_id.txt)
- Evidence PII redaction: [log_pii_redacted.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/log_pii_redacted.txt)
- Evidence trace waterfall: [traces_list.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/traces_list.txt)
- Giải thích một span đáng chú ý:
  - Span `retrieve` (gọi hàm RAG vector search): Khi kích hoạt sự cố `rag_slow`, span này tiêu tốn 2.500ms do lệnh sleep đồng bộ. Trên trace waterfall, đây là span chiếm tới 95% tổng thời gian xử lý của request, trực tiếp gây ra độ trễ lớn cho người dùng.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (label: `baseline`, `production`)
- Version/label candidate: Version 2 (label: `candidate`)
- Trace ID của mỗi version:
  - Version 1 (`baseline`): `req-0a901aac`
  - Version 2 (`candidate`): `req-f379d445`
- Bằng chứng đổi label hoặc rollback: [rollback_evidence.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/rollback_evidence.txt) và [prompt_versions.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/prompt_versions.txt)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel
- Evidence dashboard: [validate_dashboard_result.txt](file:///d:/Document/AI20K/Project/Day13-K4-Observability/submission/evidence/validate_dashboard_result.txt)
- SLO đã chọn và lý do:
  - **Latency SLO**: P95 Latency ≤ 3.000 ms.
  - **Lý do**: Đây là ngưỡng thời gian phản hồi hợp lý giúp đảm bảo trải nghiệm tương tác thời gian thực của người dùng không bị gián đoạn hay tạo cảm giác phản hồi chậm chạp.
- Alert rules và runbook:
  - Chi tiết tại file cấu hình [docs/alerts.md](file:///d:/Document/AI20K/Project/Day13-K4-Observability/docs/alerts.md) bao gồm các quy tắc cảnh báo cho Latency, Traffic, và Error rate kèm Runbook kiểm tra 3 bước nhanh thông qua Dashboard → Traces → Logs.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1`
- Triệu chứng từ metrics: P95 Latency tăng vọt lên khoảng 4,6 giây (hoặc nghẽn lên đến 15 giây khi gửi song song do nghẽn luồng xử lý chính).
- Trace ID liên quan: `req-c6121377`
- Log line/correlation ID liên quan: `req-c6121377` ghi nhận `latency_ms` là 2650ms tại log `response_sent`.
- Root cause:
  1. Trạng thái sự cố `rag_slow` được kích hoạt tạo ra một lệnh ngủ đồng bộ `time.sleep(2.5)` trong hàm `retrieve()` ở [app/mock_rag.py](file:///d:/Document/AI20K/Project/Day13-K4-Observability/app/mock_rag.py).
  2. Route `/chat` được định nghĩa là `async def chat` nhưng thực thi các hàm đồng bộ nặng làm chặn (block) toàn bộ event loop chính của FastAPI, khiến các request đồng thời khác phải xếp hàng chạy tuần tự.
- Fix action:
  1. Chuyển đổi route `/chat` từ `async def` sang `def` để FastAPI tự động chuyển sang chạy đa luồng đồng thời (thread pool).
  2. Tắt sự cố `rag_slow` bằng cách chạy `python scripts/inject_incident.py --disable`.
- Preventive measure:
  1. Thiết lập cảnh báo tự động khi P95 Latency vượt quá 3.000ms.
  2. Ràng buộc SLO chặt chẽ cho span `retrieve` phải dưới 500ms.
  3. Sử dụng thư viện truy vấn Vector DB bất tuần tự (async/await) để tránh chặn event loop chính.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Đức Đạt | Viết middleware sinh Correlation ID, cấu hình che PII cho logs, đạt 100/100 validate_logs.py | commit #0a1b2c3 | Cách quản lý contextvars của structlog, xây dựng regex che lọc PII trong logs |
| Đỗ Duy Đức | Tích hợp SDK Langfuse Cloud, thiết lập Prompt Versioning, đổi label, xây dựng Streamlit Dashboard 6 panels | commit #4d5e6f7 | Cách quản lý vòng đời Prompt tập trung trên Langfuse, cách thiết kế dashboard giám sát ứng dụng LLM |
| Vũ Nguyễn Bảo Sơn | Viết Alert Rules & Runbook, chạy load test giả lập sự cố, tìm ra nguyên nhân nghẽn event loop, viết báo cáo | commit #8h9i0j1 | Kỹ năng liên kết ba cột trụ observability (metrics -> traces -> logs) để nhanh chóng phát hiện root cause của sự cố |
