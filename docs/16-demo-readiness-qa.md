# SOSFlow demo readiness QA — 2026-07-14

## Kết luận

Local demo tại `http://localhost:5174` đã đi qua toàn bộ luồng cốt lõi bằng frontend build tĩnh, FastAPI thật và PostgreSQL. Dashboard autoplay tạo đủ 12 event; 9 report intake đều đi qua Amazon Bedrock thật trong lần kiểm cuối, không dùng fallback. Duplicate, merge, đề xuất đội, assignment, mission event, BLOCKED, NEED_REINFORCEMENT, COMPLETED, offline sync và silent zone đều có dữ liệu/API để trình bày.

## Bằng chứng kiểm thử cuối

- Backend: `40 passed`.
- Frontend: TypeScript + Vite production build pass; entry bundle được tách theo route, Reporter nằm trong offline shell.
- Migration database trắng: chạy tuần tự `20260713_01` đến `20260714_07 (head)` trên SQLite; PostgreSQL local cũng ở revision head.
- Bedrock proof: `provider=bedrock`, model/profile `apac.amazon.nova-lite-v1:0`, `fallback_used=false`, structured output hợp lệ.
- AI baseline mock: 40 records, JSON validity 100%, field extraction accuracy 94.9%; đây là baseline kỹ thuật, không phải chứng nhận chất lượng production.
- Demo protection: `/api/demo/*` trả 404 khi `DEMO_MODE=false`.
- PWA: mở Reporter online rồi reload bằng cùng browser profile ở offline vẫn render app shell và badge Offline; API/admin response không được cache.
- Dashboard autoplay: browser thật làm scenario tăng `0 → 8 → 12`, kết thúc với `complete=true` và `paused=true`.
- Scenario cuối: đủ 8 loại source, duplicate state gồm `POSSIBLE_DUPLICATE`, mission gồm `BLOCKED` và `NEED_REINFORCEMENT`, silent zone đang chờ xác minh.
- API core flow: confirm + merge giữ report gốc; verify → assign đội đề xuất → ACCEPTED → MOVING → ARRIVED → RESCUING → COMPLETED; team quay về AVAILABLE và MissionEvent có đủ từng bước.
- Admin correction: thay dữ liệu đã xác minh làm priority đổi từ `34/MEDIUM` lên `98/CRITICAL`, có audit “Priority recalculated after request data update”.

## Lỗi đã sửa trong vòng QA này

1. **Start không autoplay**: Dashboard giờ phát tuần tự event theo x1/x2/x5, pause/unmount hủy timer; đổi speed không reset scenario.
2. **Reset scenario có thể HTTP 500**: không còn xóa demo team đang được mission audit của report thật tham chiếu; reset cũng dọn duplicate warning bị stale trên report thật.
3. **Fresh migration fail**: revision intake mode giờ idempotent cho cả database trắng và database legacy.
4. **Mission UI cho transition sai**: Rescue view chỉ hiện các bước hợp lệ theo transition matrix, có loading/error/success và mission timeline.
5. **Thiếu admin correction UI**: Request Detail cho sửa fact đã xác minh và kích hoạt analyzer/priority recalculation.
6. **Thiếu merge summary**: Request Detail hiển thị incident chính, số report đã gộp và giữ liên kết report gốc.
7. **PWA không hoạt động ở container demo**: frontend chuyển từ Vite dev sang bundle build tĩnh; service worker cache cả content-hashed assets.
8. **Offline retry có thể tạo trùng**: queue giữ nguyên `client_submission_id` của lần gửi đầu; validation 4xx không bị hiểu nhầm thành mất mạng.
9. **AI evaluation command bị hỏng**: bổ sung schema, 40 mẫu synthetic, training/validation examples và field extraction metric.
10. **Bundle quá lớn**: tách các màn hình admin/map theo route, giữ Reporter trong entry bundle để offline-first.
11. **Mobile bị tràn ngang**: khóa min-width của command grid/sidebar và kiểm visual Reporter ở viewport 390px.

## Giới hạn cố ý — không được nói quá khi demo

- SMS, Zalo và 112 là simulator, không phải gateway production.
- Chưa có authentication/authorization; chỉ chạy local hoặc mạng demo tin cậy.
- Khoảng cách đội là Haversine đường thẳng, không phải ETA hay routing đường bộ.
- Silent zone chỉ có nghĩa “cần xác minh”.
- What3words chỉ là liên kết tham chiếu; không gọi API What3words.
- Chưa có ảnh offline, audio transcription hoặc Background Sync API; hiện dùng IndexedDB, online event, manual sync và backoff.
- OSM map tile cần Internet; report thiếu tile vẫn còn trong bảng/API.
- Chưa có Playwright suite trong CI. Core lifecycle có API-level E2E tự động; browser headless đã được dùng để kiểm visual, PWA offline và autoplay cho release demo này.

## Cách chạy lại

```bash
DEMO_TOKEN=sosflow-demo docker compose -p sosflowlocaldemo -f docker-compose.local-demo.yml up -d --build
```

Mở `http://localhost:5174/admin/dashboard`, bấm **Bắt đầu mô phỏng**. Nếu muốn trạng thái xác định trước phần trình bày, bấm **Đặt lại** rồi **Bắt đầu mô phỏng**.
