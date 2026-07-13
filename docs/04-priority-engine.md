# Priority Engine

```text
priority_score =
severity_score
+ people_score
+ vulnerable_score
+ injury_score
+ trapped_score
+ water_level_score
+ waiting_time_score
```

Trọng số nằm trong `config/priority-rules.yaml`.

Mức ưu tiên:

- 0-29: LOW
- 30-49: MEDIUM
- 50-69: HIGH
- 70 trở lên: CRITICAL

Ví dụ: yêu cầu có nội dung "sắp chết", 6 người, 2 trẻ em, 1 người bị thương, mắc kẹt và nước 2,6m sẽ nhận điểm từ nguy hiểm tính mạng, số người, nhóm dễ tổn thương, thương tích, mắc kẹt và mực nước.

Thời gian chờ: cứ mỗi 10 phút chưa hoàn tất xử lý cộng 1 điểm, tối đa 15 điểm.

AI chỉ hỗ trợ đề xuất. Ban Chỉ huy là người quyết định cuối cùng.
