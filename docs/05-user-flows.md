# User Flows

## Gửi SOS

Người dân nhập thông tin, backend validate, lưu database, phân tích nội dung, tính điểm ưu tiên và trả mã yêu cầu.

## Xác minh

Ban Chỉ huy mở dashboard, lọc request, xem chi tiết, lý do ưu tiên và thông tin thiếu.

## Phân công cứu hộ

Điều phối viên chọn đội cứu hộ và ghi chú. Request chuyển sang `ASSIGNED`, mission được tạo.

## Cập nhật trạng thái

Đội cứu hộ cập nhật `ACCEPTED`, `MOVING`, `ARRIVED`, `RESCUING`, `COMPLETED` hoặc `FAILED`.

## Hoàn thành

Khi mission hoàn thành, request chuyển `COMPLETED`, đội cứu hộ trở lại `AVAILABLE`.

## Vòng đời trạng thái

```text
PENDING_VERIFICATION
-> ASSIGNED
-> ACCEPTED
-> MOVING
-> ARRIVED
-> RESCUING
-> COMPLETED
```

Nếu nhiệm vụ không thể hoàn thành, đội cứu hộ có thể chuyển sang `FAILED` và ghi chú lý do hiện trường.
