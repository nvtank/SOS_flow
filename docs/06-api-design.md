# API Design

## Reporter

`POST /api/rescue-requests`

```json
{
  "reporter_name": "Nguyễn Văn An",
  "phone_number": "0912000001",
  "message": "Nhà tôi có 5 người, nước đang lên nhanh",
  "address": "Đà Nẵng",
  "number_of_people": 5
}
```

`GET /api/rescue-requests/{request_code}/status`

## Command Center

- `GET /api/admin/rescue-requests`
- `GET /api/admin/rescue-requests/{id}`
- `PATCH /api/admin/rescue-requests/{id}`
- `POST /api/admin/rescue-requests/{id}/assign`
- `GET /api/admin/statistics`

Filter hỗ trợ `status`, `priority_level`, `source`, `assigned_team_id`, `search`.

## Rescue Team

- `GET /api/rescue-teams`
- `POST /api/rescue-teams`
- `GET /api/rescue-teams/{id}/missions`
- `PATCH /api/missions/{id}/status`

Mã lỗi cơ bản: `400` cho dữ liệu không hợp lệ, `404` khi không tìm thấy, `422` cho validation của FastAPI.
