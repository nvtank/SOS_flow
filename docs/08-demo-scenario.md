# Demo Scenario

1. Người dân mở `/report` và gửi tin: "Nhà tôi có 5 người, 2 trẻ em, nước đang lên rất nhanh, chúng tôi không ra được."
2. API tạo mã `SOS-xxxx`, mock analyzer phát hiện trapped và high_water.
3. Priority Engine tính điểm và phân loại HIGH hoặc CRITICAL tùy dữ liệu nhập.
4. Ban Chỉ huy mở `/admin/dashboard` và thấy request mới trên bảng, bản đồ.
5. Điều phối viên mở chi tiết request, đọc lý do ưu tiên và giao đội xuồng cứu hộ.
6. Đội cứu hộ mở `/rescue/1/missions`, cập nhật `ACCEPTED`, `MOVING`, `ARRIVED`, `RESCUING`.
7. Khi cứu hộ xong, đội cập nhật `COMPLETED`.

Checklist khi demo:

- Mở sẵn API docs để chứng minh backend có endpoint thật.
- Gửi một request mới từ Reporter thay vì chỉ dùng seed data.
- Chỉ rõ phần reasons để giải thích vì sao request được ưu tiên.
- Sau khi assign, chuyển sang màn hình Rescue Team để cập nhật trạng thái.
