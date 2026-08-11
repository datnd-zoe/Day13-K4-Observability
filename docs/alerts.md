# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: Chat Latency P95 Exceeded (Độ trễ P95 của chat vượt ngưỡng)
- Severity: Warning
- SLI/SLO liên quan: SLO Latency P95 ≤ 3.000 ms
- Điều kiện và thời gian duy trì: P95 Latency của endpoint `/chat` > 3.000 ms kéo dài liên tục trong 1 phút.
- Ảnh hưởng tới người dùng: Người dùng phải chờ đợi lâu để nhận được câu trả lời, giảm trải nghiệm tương tác trực tiếp.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard: Xem panel "Latency percentiles" để xem độ trễ trung bình và P95 hiện tại.
  2. Tra cứu Langfuse: Mở các trace chậm trong khoảng thời gian cảnh báo, xem biểu đồ Waterfall để xác định span nào bị chậm (ví dụ: `retrieve` hay `generation`).
  3. Lục Log: Lấy `correlation_id` từ trace chậm trên Langfuse và lọc log tương ứng trong `logs.jsonl` để kiểm tra thông tin chi tiết của request.
- Mitigation tạm thời:
  - Tắt kịch bản sự cố `rag_slow` nếu đang được kích hoạt.
  - Tăng thời gian lưu cache (TTL) cho kết quả RAG hoặc LLM.
  - Hạn chế số lượng documents trả về từ RAG để giảm thời gian xử lý.
- Owner: Đỗ Duy Đức

## Alert 2

- Tên: Chat Error Rate High (Tỷ lệ lỗi chat tăng cao)
- Severity: Critical
- SLI/SLO liên quan: SLO Error Rate ≤ 2%
- Điều kiện và thời gian duy trì: Tỷ lệ lỗi trên tổng số requests nhận được > 2% kéo dài liên tục trong 1 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận được phản hồi lỗi (HTTP 500) và không nhận được câu trả lời từ AI.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard: Xem panel "Error rate and breakdown" để biết lỗi thuộc loại nào (`error_type`).
  2. Tra cứu Langfuse: Lọc các trace lỗi để xác định lỗi xuất hiện ở span nào (ví dụ: RAG timeout hay LLM API error).
  3. Lục Log: Tìm các dòng log có `level == "error"` hoặc chứa thông tin ngoại lệ cùng `correlation_id` để đọc stack trace lỗi.
- Mitigation tạm thời:
  - Bật cơ chế fallback sang mô hình LLM dự phòng hoặc trả về câu trả lời mặc định được cấu hình sẵn.
  - Khởi động lại service FastAPI nếu phát hiện lỗi nghẽn hoặc treo luồng.
- Owner: Nguyễn Đức Đạt

## Alert 3

- Tên: Cost Spike Alert (Chi phí LLM tăng vọt)
- Severity: Warning
- SLI/SLO liên quan: SLO Tổng chi phí trong 60 phút ≤ 2.5 USD
- Điều kiện và thời gian duy trì: Tổng chi phí tích lũy trong vòng 60 phút qua vượt quá 2.5 USD.
- Ảnh hưởng tới người dùng: Nguy cơ cạn kiệt ngân sách dự án và làm gián đoạn hệ thống nếu API key bị khóa.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard: Xem panel "Cost over time" và "Input and output tokens" để biết tổng token tiêu thụ.
  2. Tra cứu Langfuse: Lọc tìm các trace có cost lớn nhất và kiểm tra nội dung prompt/generation xem có chứa tài liệu quá dài hay lặp từ.
  3. Lục Log: Tìm log của các request có chi phí cao, đối chiếu user_id_hash để phát hiện hành vi spam/abusive.
- Mitigation tạm thời:
  - Cấu hình giảm `max_tokens` cho câu trả lời của LLM.
  - Giảm bớt số lượng tài liệu tham chiếu (docs) truyền vào prompt.
  - Tạm thời khóa/giới hạn tần suất request (rate limit) đối với các user tiêu tốn nhiều token nhất.
- Owner: Vũ Nguyễn Bảo Sơn
