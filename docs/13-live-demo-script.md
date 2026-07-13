# Live demo — Lũ quét và sạt lở Trà Linh (3–5 phút)

## Chuẩn bị

1. Khởi động với `DEMO_MODE=true DEMO_TOKEN=sosflow-demo docker compose up --build`.
2. Mở ba tab: `/report`, `/admin/dashboard`, và một Request Detail.
3. Trên Dashboard, dùng **Start x1** để reset scenario về trạng thái xác định. Demo panel chỉ xuất hiện trong `DEMO_MODE`; API demo yêu cầu `X-Demo-Token`.

## Lời dẫn và thao tác

1. Ở Reporter, chuyển DevTools sang Offline, gửi một SOS. Mã `LOCAL-...` xuất hiện cùng thông báo dữ liệu nằm trên thiết bị.
2. Reload trang khi vẫn Offline để cho thấy queue còn nguyên. Bật mạng và bấm **Đồng bộ ngay**. Dashboard nhận report với nguồn `OFFLINE_SYNC`; thời điểm local và server sync được lưu riêng.
3. Mở Dashboard, bấm **Bơm event kế** vài lần: gọi 112, SMS sai chính tả, Web, Zalo simulator và cán bộ xã đi qua cùng pipeline. Chỉ rõ badge “Nghi trùng”. Đây đều là simulator, không phải SMS/Zalo/112 production.
4. Bấm **Bơm tất cả**. Charts, alert Critical chưa giao đội, mission BLOCKED, NEED_REINFORCEMENT và vòng tròn vùng im lặng cần xác minh tại Trà Linh cập nhật qua API thật.
5. Mở một request Critical để xem summary AI, confidence, lý do priority và top đội gợi ý. Điều phối viên vẫn bấm assign thủ công.
6. Trên Rescue app, chuyển mission theo `ACCEPTED → MOVING → ARRIVED → RESCUING → COMPLETED`; quay lại Dashboard để thấy số hoàn thành tăng.
7. Chọn vùng im lặng và bấm “Đang xác minh”, “An toàn” hoặc “Cần cứu hộ”. Giải thích đây chỉ là tín hiệu cần xác minh, không kết luận có nạn nhân.

## Fallback và reset

Nếu Bedrock timeout, request vẫn được tạo với analyzer mock và badge fallback; không cố gọi lại AWS trong lúc trình bày. Dùng **Reset** để xóa riêng dữ liệu simulator và các team demo, không xóa báo cáo production. Start lại scenario trước lần demo tiếp theo.
