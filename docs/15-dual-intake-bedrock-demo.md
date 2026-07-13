# Demo hai luồng tiếp nhận: rule-based và Amazon Bedrock

## Mục đích

Reporter tại `http://localhost:5174/report` có hai lựa chọn nhưng vẫn gọi chung `POST /api/rescue-requests`.

- **Biểu mẫu có cấu trúc (`STRUCTURED`)**: backend tính tổng người từ người lớn + trẻ em, không gọi AI, sau đó chạy Priority Engine.
- **Mô tả tự nhiên (`NATURAL_LANGUAGE`)**: backend gọi Amazon Bedrock Converse để trích xuất structured output, xác thực lại dữ kiện và chạy cùng Priority Engine.

Priority Engine là nguồn điểm chính thức ở cả hai luồng. Bedrock không tự giao đội và không tự phát lệnh cứu hộ.

## Chuẩn bị

Đặt cấu hình Bedrock trong `.env` ở root repo, không commit AWS credentials:

```env
AI_PROVIDER=bedrock
AWS_REGION=ap-southeast-1
BEDROCK_INFERENCE_PROFILE_ARN=apac.amazon.nova-lite-v1:0
AI_FALLBACK_ENABLED=true
```

SDK sử dụng default credential chain. Trên ECS phải dùng Task Role; local có thể dùng AWS profile.

Khởi động:

```bash
DEMO_TOKEN=sosflow-demo docker compose -p sosflowlocaldemo -f docker-compose.local-demo.yml up -d --build
```

Mở `http://localhost:5174/report`.

## Luồng 1 — dữ liệu cố định, không AI

Chọn **Biểu mẫu có cấu trúc** và nhập:

- Họ tên: `Nguyen Van A`
- Người lớn: `2`
- Trẻ em: `3`
- Người cao tuổi: `1`
- Bị thương: `1`
- Mực nước: `2.2`
- Địa chỉ: `Trà Linh, Đà Nẵng`
- Đánh dấu đang mắc kẹt

Kết quả mong đợi:

- `number_of_people=5`
- `provider=rule_based`
- `ai_invoked=false`
- `fallback_used=false`
- priority được tính và giải thích bằng rules.

## Luồng 2 — văn bản tự nhiên qua Bedrock

Chọn **Mô tả tự nhiên** và nhập:

```text
cứu tôi với tôi sắp trụ không nổi rồi tôi ở Trà Linh đang có mẹ già, dự kiến không sống qua nổi 9 giờ vì nước dâng quá cao
```

Kết quả chỉ được xem là gọi Bedrock thật khi trang thành công và Request Detail cùng hiển thị:

- `provider=bedrock`
- `requested_provider=bedrock`
- `bedrock_succeeded=true`
- `fallback_used=false`
- model ID/inference profile và latency lớn hơn 0.

Với câu trên, lớp validation giữ `water_level=null` vì người báo không đưa số đo cụ thể; cụm “nước quá cao” chỉ tạo risk `high_water`. Cụm “tôi ... có mẹ già” được chuẩn hóa thành ít nhất 2 người và 1 người cao tuổi. Cụm “không sống qua/không trụ nổi” tạo lý do nguy cơ không thể cầm cự trong Priority Engine.

Địa danh Trà Linh được nối tới tâm tham chiếu demo bằng gazetteer cục bộ. Đây là tọa độ phục vụ demo Haversine, không phải geocoding production hoặc GPS chính xác của nạn nhân.

## Chứng minh điều phối hoàn chỉnh

1. Mở Request Detail của report Bedrock.
2. Kiểm tra marker sự cố, trạm/đội và top 3 đề xuất có khoảng cách đường thẳng.
3. Bấm **Xác minh yêu cầu**.
4. Chọn một đội `AVAILABLE` rồi bấm **Giao nhiệm vụ**.
5. Trong Rescue Team View cập nhật `ACCEPTED → MOVING → BLOCKED → MOVING → ARRIVED → RESCUING → COMPLETED`.
6. Xác nhận timeline có đủ actor/note/timestamp, đội trở lại `AVAILABLE`, active mission về 0 và Dashboard tăng số Completed.

## Kiểm thử

```bash
AI_PROVIDER=mock DEMO_TOKEN=sosflow-demo docker compose -p sosflowlocaldemo -f docker-compose.local-demo.yml run --rm --build --no-deps --entrypoint sh backend -c 'python -m pytest -q'
cd frontend && npm run build
```

Test mock Bedrock để kiểm tra schema/failure; minh chứng invocation thật phải lấy từ metadata của report chạy với AWS permission hợp lệ.
