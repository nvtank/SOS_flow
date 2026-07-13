# Limitations

Current MVP chưa có:

- SMS Gateway thật.
- Zalo API thật.
- Xử lý cuộc gọi thật.
- AI production.
- Dữ liệu thời tiết thời gian thực.
- Tối ưu tuyến đường.
- Deduplication hoàn chỉnh.
- Xác thực và phân quyền production.

Các giả lập đang dùng:

- Mock AI analyzer dựa trên từ khóa.
- Đăng nhập giả lập bằng đường dẫn.
- Redis mới là placeholder kiến trúc.

Trước khi dùng cho môi trường thật, hệ thống cần bổ sung xác thực, phân quyền, audit log, bảo vệ dữ liệu cá nhân, giám sát hạ tầng và quy trình xác minh thông tin với cơ quan phụ trách.
