# Limitations

Current MVP chưa có:

- SMS Gateway thật.
- Zalo API thật.
- Xử lý cuộc gọi thật.
- Custom/fine-tuned Bedrock model đã được đánh giá cho production.
- Dữ liệu thời tiết thời gian thực.
- Tối ưu tuyến đường.
- Semantic/embedding deduplication quy mô lớn; MVP đang dùng heuristic có lý do giải thích được và admin quyết định.
- Xác thực và phân quyền production.

Các giả lập đang dùng:

- SMS, Zalo và cuộc gọi 112 chỉ là source simulator.
- Mock analyzer là fallback; khi `AI_PROVIDER=bedrock` và IAM hợp lệ, web gọi Bedrock Converse thật và lưu metadata minh chứng.
- Không có đăng nhập/phân quyền; các đường dẫn admin/rescue chỉ dành cho demo local.
- Redis mới là placeholder kiến trúc.

Trước khi dùng cho môi trường thật, hệ thống cần bổ sung xác thực, phân quyền, audit log, bảo vệ dữ liệu cá nhân, giám sát hạ tầng và quy trình xác minh thông tin với cơ quan phụ trách.
