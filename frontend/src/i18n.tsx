import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

export type Language = "vi" | "en" | "ko";

const messages: Record<Language, Record<string, string>> = {
  vi: {
    "nav.dashboard": "Tổng quan", "nav.requests": "Tin báo", "nav.teams": "Đội cứu hộ", "nav.report": "Gửi SOS",
    "layout.commandCenter": "Trung tâm điều phối", "layout.live": "Hệ thống đang hoạt động", "layout.guide": "Hướng dẫn", "layout.language": "Ngôn ngữ",
    "guide.title": "Hướng dẫn sử dụng SOSFlow", "guide.subtitle": "Quy trình chuẩn từ lúc nhận tin đến khi hoàn thành cứu hộ.",
    "guide.step1.title": "1. Tiếp nhận", "guide.step1.body": "Tin từ Web, 112, SMS hoặc cán bộ địa phương xuất hiện trên Dashboard.",
    "guide.step2.title": "2. Xác minh", "guide.step2.body": "Mở chi tiết, kiểm tra AI, vị trí, người cần cứu và tin nghi trùng.",
    "guide.step3.title": "3. Điều phối", "guide.step3.body": "Xác minh tin, xem 3 đội đề xuất rồi chủ động giao nhiệm vụ.",
    "guide.step4.title": "4. Theo dõi", "guide.step4.body": "Theo dõi MOVING → ARRIVED → RESCUING và xử lý BLOCKED hoặc tăng cường.",
    "guide.step5.title": "5. Hoàn tất", "guide.step5.body": "Xác nhận COMPLETED, kiểm tra timeline và số liệu tổng hợp.",
    "guide.tip": "Mẹo: ưu tiên cảnh báo màu đỏ và tin Critical chưa có đội trước.", "common.close": "Đóng", "common.open": "Mở", "common.refresh": "Làm mới", "common.loading": "Đang tải…", "common.noData": "Chưa có dữ liệu",
    "dashboard.title": "Tổng quan điều phối", "dashboard.subtitle": "Theo dõi toàn bộ tin báo và tiến độ cứu hộ theo thời gian gần thực.",
    "dashboard.updated": "Cập nhật", "dashboard.autoRefresh": "Tự làm mới mỗi 5 giây", "dashboard.total": "Tổng tin báo", "dashboard.totalHint": "Tất cả nguồn",
    "dashboard.critical": "Mức nguy cấp", "dashboard.criticalHint": "Cần xử lý trước", "dashboard.pending": "Chờ xác minh", "dashboard.pendingHint": "Cần điều phối viên",
    "dashboard.active": "Đang cứu hộ", "dashboard.activeHint": "Nhiệm vụ đang chạy", "dashboard.completed": "Hoàn thành", "dashboard.completedHint": "Đã kết thúc",
    "dashboard.available": "Đội sẵn sàng", "dashboard.availableHint": "Có thể phân công", "dashboard.map": "Bản đồ sự cố", "dashboard.mapHint": "Nhấn marker để mở chi tiết",
    "dashboard.actions": "Cần xử lý ngay", "dashboard.noAlerts": "Không có cảnh báo đang mở", "dashboard.silentZones": "Khu vực cần xác minh", "dashboard.missingLocation": "Tin thiếu vị trí",
    "dashboard.sourceChart": "Nguồn tiếp nhận", "dashboard.statusChart": "Trạng thái tin báo", "dashboard.priorityChart": "Cơ cấu ưu tiên", "dashboard.timelineChart": "Lượng tin theo thời gian",
    "dashboard.flow": "Luồng cứu hộ", "dashboard.flowHint": "Số hồ sơ đang nằm ở từng bước", "dashboard.priorityList": "Sự cố ưu tiên", "dashboard.viewAll": "Xem toàn bộ",
    "dashboard.avgWait": "Chờ trung bình", "dashboard.avgAssign": "Thời gian giao đội", "dashboard.avgArrive": "Đến hiện trường", "dashboard.avgComplete": "Hoàn tất nhiệm vụ",
    "dashboard.code": "Mã", "dashboard.source": "Nguồn", "dashboard.location": "Vị trí", "dashboard.score": "Điểm", "dashboard.status": "Trạng thái", "dashboard.team": "Đội",
    "dashboard.demoTitle": "Lũ quét và sạt lở Trà Linh", "dashboard.demoStart": "Bắt đầu mô phỏng", "dashboard.next": "Sự kiện kế", "dashboard.injectAll": "Bơm tất cả", "dashboard.reset": "Đặt lại",
    "requests.title": "Danh sách tin báo", "requests.subtitle": "Tìm kiếm, lọc và xử lý hàng đợi theo mức ưu tiên.", "teams.title": "Đội cứu hộ", "teams.subtitle": "Theo dõi năng lực và mở nhiệm vụ hiện trường của từng đội.",
    "report.title": "Gửi yêu cầu cứu hộ", "report.subtitle": "Cung cấp những thông tin bạn biết. Báo cáo vẫn được lưu khi mất Internet.",
    "success.title": "Yêu cầu đã được tiếp nhận", "success.keepPhone": "Hãy giữ điện thoại trong trạng thái có thể liên lạc.", "success.another": "Gửi yêu cầu khác",
    "form.online": "Đang có kết nối", "form.offline": "Ngoại tuyến", "form.name": "Họ tên", "form.phone": "Số điện thoại", "form.message": "Nội dung cầu cứu", "form.messageHint": "Ví dụ: Nhà tôi có 5 người, nước đang lên rất nhanh…", "form.address": "Địa chỉ hoặc mô tả vị trí", "form.people": "Số người", "form.children": "Trẻ em", "form.elderly": "Người cao tuổi", "form.injured": "Bị thương", "form.water": "Mực nước ước tính (mét)", "form.note": "Ghi chú bổ sung", "form.trapped": "Đang mắc kẹt", "form.disabled": "Có người khuyết tật", "form.pregnant": "Có phụ nữ mang thai", "form.send": "Gửi SOS", "form.sending": "Đang gửi", "form.saveOffline": "Lưu SOS trên thiết bị", "form.localReports": "Báo cáo lưu trên thiết bị", "form.syncNow": "Đồng bộ ngay", "form.noQueue": "Không có báo cáo chờ đồng bộ.",
    "requests.search": "Tìm mã, địa chỉ, nội dung", "requests.allSources": "Mọi nguồn", "requests.allPriorities": "Mọi ưu tiên", "requests.allStatuses": "Mọi trạng thái", "requests.allAssignments": "Mọi phân công", "requests.assigned": "Đã giao", "requests.unassigned": "Chưa giao", "requests.highest": "Điểm cao nhất", "requests.newest": "Mới nhất", "requests.oldest": "Cũ nhất", "requests.recent": "Cập nhật gần đây", "requests.time": "Thời gian", "requests.people": "Số người", "requests.wait": "Chờ", "requests.level": "Mức", "requests.detail": "Chi tiết", "requests.previous": "Trước", "requests.next": "Sau", "requests.page": "Trang", "requests.empty": "Không có tin báo phù hợp.",
    "teams.members": "thành viên", "teams.openMission": "Mở nhiệm vụ", "teams.empty": "Chưa có đội cứu hộ.", "mission.title": "Nhiệm vụ đội cứu hộ", "mission.subtitle": "Cập nhật trạng thái hiện trường để trung tâm theo dõi vòng đời nhiệm vụ.", "mission.empty": "Đội này chưa có nhiệm vụ được giao.", "mission.contact": "Liên hệ", "mission.address": "Địa chỉ", "mission.people": "Số người", "mission.injured": "Bị thương", "mission.note": "Ghi chú hiện trường",
    "detail.sender": "Người gửi", "detail.phone": "Điện thoại", "detail.address": "Địa chỉ", "detail.people": "Số người", "detail.children": "Trẻ em", "detail.elderly": "Người cao tuổi", "detail.injured": "Bị thương", "detail.water": "Mực nước", "detail.received": "Thời điểm nhận", "detail.unknown": "Chưa rõ", "detail.missingLocation": "Thiếu vị trí", "detail.priority": "Giải thích điểm ưu tiên", "detail.duplicates": "Báo cáo nghi trùng", "detail.confirm": "Xác nhận", "detail.reject": "Từ chối", "detail.merge": "Gộp vào", "detail.analysis": "Phân tích hỗ trợ", "detail.reanalyze": "Phân tích lại", "detail.noSummary": "Chưa có tóm tắt", "detail.risks": "Rủi ro nhận diện", "detail.missing": "Thông tin còn thiếu", "detail.confidence": "Độ tin cậy", "detail.none": "Không có", "detail.timeline": "Dòng thời gian", "detail.noHistory": "Chưa có lịch sử", "detail.recommendations": "Đội đề xuất", "detail.noDistance": "Chưa tính được khoảng cách", "detail.straightDistance": "km đường thẳng", "detail.noVehicle": "Chưa rõ phương tiện", "detail.noTeam": "Chưa có đội sẵn sàng phù hợp hoặc dữ liệu vị trí còn thiếu.", "detail.assignment": "Phân công đội cứu hộ", "detail.source": "Nguồn", "detail.verify": "Xác minh yêu cầu", "detail.chooseTeam": "Chọn đội", "detail.dispatchNote": "Ghi chú điều phối", "detail.assign": "Giao nhiệm vụ", "detail.raw": "JSON kỹ thuật", "detail.openW3w": "Mở vị trí trên What3words", "success.code": "Mã yêu cầu", "success.status": "Trạng thái", "success.missing": "Không tìm thấy thông tin yêu cầu vừa gửi."
  },
  en: {
    "nav.dashboard": "Overview", "nav.requests": "Reports", "nav.teams": "Rescue teams", "nav.report": "Send SOS",
    "layout.commandCenter": "Command center", "layout.live": "System operational", "layout.guide": "User guide", "layout.language": "Language",
    "guide.title": "How to use SOSFlow", "guide.subtitle": "The standard workflow from intake to rescue completion.",
    "guide.step1.title": "1. Intake", "guide.step1.body": "Reports from Web, 112, SMS, or local officers appear on the Dashboard.",
    "guide.step2.title": "2. Verify", "guide.step2.body": "Open details and review AI analysis, location, people at risk, and duplicates.",
    "guide.step3.title": "3. Dispatch", "guide.step3.body": "Verify the report, review the top three teams, then assign manually.",
    "guide.step4.title": "4. Track", "guide.step4.body": "Track MOVING → ARRIVED → RESCUING and respond to BLOCKED or reinforcement requests.",
    "guide.step5.title": "5. Complete", "guide.step5.body": "Confirm COMPLETED, review the timeline, and verify operational metrics.",
    "guide.tip": "Tip: handle red alerts and unassigned Critical reports first.", "common.close": "Close", "common.open": "Open", "common.refresh": "Refresh", "common.loading": "Loading…", "common.noData": "No data yet",
    "dashboard.title": "Operations overview", "dashboard.subtitle": "Monitor incoming reports and rescue progress in near real time.",
    "dashboard.updated": "Updated", "dashboard.autoRefresh": "Auto-refresh every 5 seconds", "dashboard.total": "Total reports", "dashboard.totalHint": "All channels",
    "dashboard.critical": "Critical", "dashboard.criticalHint": "Handle first", "dashboard.pending": "Awaiting verification", "dashboard.pendingHint": "Operator action needed",
    "dashboard.active": "Active rescues", "dashboard.activeHint": "Missions in progress", "dashboard.completed": "Completed", "dashboard.completedHint": "Missions closed",
    "dashboard.available": "Available teams", "dashboard.availableHint": "Ready to dispatch", "dashboard.map": "Incident map", "dashboard.mapHint": "Select a marker to open details",
    "dashboard.actions": "Action required", "dashboard.noAlerts": "No open alerts", "dashboard.silentZones": "Zones to verify", "dashboard.missingLocation": "Missing location",
    "dashboard.sourceChart": "Intake channels", "dashboard.statusChart": "Report status", "dashboard.priorityChart": "Priority mix", "dashboard.timelineChart": "Reports over time",
    "dashboard.flow": "Rescue workflow", "dashboard.flowHint": "Reports currently at each stage", "dashboard.priorityList": "Priority incidents", "dashboard.viewAll": "View all",
    "dashboard.avgWait": "Average wait", "dashboard.avgAssign": "Time to assign", "dashboard.avgArrive": "Time to arrive", "dashboard.avgComplete": "Time to complete",
    "dashboard.code": "Code", "dashboard.source": "Source", "dashboard.location": "Location", "dashboard.score": "Score", "dashboard.status": "Status", "dashboard.team": "Team",
    "dashboard.demoTitle": "Tra Linh flash flood and landslide", "dashboard.demoStart": "Start simulation", "dashboard.next": "Next event", "dashboard.injectAll": "Inject all", "dashboard.reset": "Reset",
    "requests.title": "Emergency reports", "requests.subtitle": "Search, filter, and process the priority queue.", "teams.title": "Rescue teams", "teams.subtitle": "Review team capacity and open field missions.",
    "report.title": "Send a rescue request", "report.subtitle": "Share what you know. Your report remains saved when the Internet is unavailable.",
    "success.title": "Your request was received", "success.keepPhone": "Please keep your phone available for contact.", "success.another": "Send another request",
    "form.online": "Online", "form.offline": "Offline", "form.name": "Full name", "form.phone": "Phone number", "form.message": "Emergency message", "form.messageHint": "Example: Five people are trapped and the water is rising quickly…", "form.address": "Address or location description", "form.people": "People", "form.children": "Children", "form.elderly": "Elderly", "form.injured": "Injured", "form.water": "Estimated water level (m)", "form.note": "Additional note", "form.trapped": "Currently trapped", "form.disabled": "Person with disability", "form.pregnant": "Pregnant person", "form.send": "Send SOS", "form.sending": "Sending", "form.saveOffline": "Save SOS on device", "form.localReports": "Reports stored on device", "form.syncNow": "Sync now", "form.noQueue": "No reports waiting to sync.",
    "requests.search": "Search code, address, or message", "requests.allSources": "All sources", "requests.allPriorities": "All priorities", "requests.allStatuses": "All statuses", "requests.allAssignments": "All assignments", "requests.assigned": "Assigned", "requests.unassigned": "Unassigned", "requests.highest": "Highest score", "requests.newest": "Newest", "requests.oldest": "Oldest", "requests.recent": "Recently updated", "requests.time": "Time", "requests.people": "People", "requests.wait": "Waiting", "requests.level": "Level", "requests.detail": "Details", "requests.previous": "Previous", "requests.next": "Next", "requests.page": "Page", "requests.empty": "No matching reports.",
    "teams.members": "members", "teams.openMission": "Open mission", "teams.empty": "No rescue teams.", "mission.title": "Rescue team missions", "mission.subtitle": "Update field status so the command center can track each mission.", "mission.empty": "This team has no assigned mission.", "mission.contact": "Contact", "mission.address": "Address", "mission.people": "People", "mission.injured": "Injured", "mission.note": "Field note",
    "detail.sender": "Reporter", "detail.phone": "Phone", "detail.address": "Address", "detail.people": "People", "detail.children": "Children", "detail.elderly": "Elderly", "detail.injured": "Injured", "detail.water": "Water level", "detail.received": "Received at", "detail.unknown": "Unknown", "detail.missingLocation": "Missing location", "detail.priority": "Priority score explanation", "detail.duplicates": "Possible duplicates", "detail.confirm": "Confirm", "detail.reject": "Reject", "detail.merge": "Merge into", "detail.analysis": "AI-assisted analysis", "detail.reanalyze": "Analyze again", "detail.noSummary": "No summary yet", "detail.risks": "Detected risks", "detail.missing": "Missing information", "detail.confidence": "Confidence", "detail.none": "None", "detail.timeline": "Timeline", "detail.noHistory": "No history yet", "detail.recommendations": "Recommended teams", "detail.noDistance": "Distance unavailable", "detail.straightDistance": "km straight-line", "detail.noVehicle": "Vehicle unknown", "detail.noTeam": "No suitable available team or location data is missing.", "detail.assignment": "Assign rescue team", "detail.source": "Source", "detail.verify": "Verify report", "detail.chooseTeam": "Choose a team", "detail.dispatchNote": "Dispatch note", "detail.assign": "Assign mission", "detail.raw": "technical JSON", "detail.openW3w": "Open location in What3words", "success.code": "Request code", "success.status": "Status", "success.missing": "The submitted request could not be found."
  },
  ko: {
    "nav.dashboard": "종합 현황", "nav.requests": "신고 목록", "nav.teams": "구조팀", "nav.report": "SOS 보내기",
    "layout.commandCenter": "재난 지휘 센터", "layout.live": "시스템 정상 운영", "layout.guide": "사용 안내", "layout.language": "언어",
    "guide.title": "SOSFlow 사용 안내", "guide.subtitle": "신고 접수부터 구조 완료까지의 표준 절차입니다.",
    "guide.step1.title": "1. 접수", "guide.step1.body": "웹, 112, SMS, 지역 담당자의 신고가 대시보드에 표시됩니다.",
    "guide.step2.title": "2. 확인", "guide.step2.body": "상세 화면에서 AI 분석, 위치, 구조 인원, 중복 신고를 확인합니다.",
    "guide.step3.title": "3. 배정", "guide.step3.body": "신고를 확인하고 추천 구조팀 3곳을 검토한 뒤 직접 배정합니다.",
    "guide.step4.title": "4. 추적", "guide.step4.body": "MOVING → ARRIVED → RESCUING 진행과 BLOCKED 또는 지원 요청을 추적합니다.",
    "guide.step5.title": "5. 완료", "guide.step5.body": "COMPLETED를 확인하고 타임라인과 운영 지표를 검토합니다.",
    "guide.tip": "팁: 빨간 경고와 아직 팀이 배정되지 않은 Critical 신고를 먼저 처리하세요.", "common.close": "닫기", "common.open": "열기", "common.refresh": "새로고침", "common.loading": "불러오는 중…", "common.noData": "데이터 없음",
    "dashboard.title": "운영 종합 현황", "dashboard.subtitle": "신고 접수와 구조 진행 상황을 실시간에 가깝게 확인합니다.",
    "dashboard.updated": "업데이트", "dashboard.autoRefresh": "5초마다 자동 새로고침", "dashboard.total": "전체 신고", "dashboard.totalHint": "모든 채널",
    "dashboard.critical": "긴급", "dashboard.criticalHint": "최우선 처리", "dashboard.pending": "확인 대기", "dashboard.pendingHint": "운영자 확인 필요",
    "dashboard.active": "구조 진행", "dashboard.activeHint": "진행 중 임무", "dashboard.completed": "완료", "dashboard.completedHint": "종료된 임무",
    "dashboard.available": "대기 구조팀", "dashboard.availableHint": "배정 가능", "dashboard.map": "사고 지도", "dashboard.mapHint": "마커를 눌러 상세 보기",
    "dashboard.actions": "즉시 조치", "dashboard.noAlerts": "열린 경고 없음", "dashboard.silentZones": "확인 필요 지역", "dashboard.missingLocation": "위치 정보 없음",
    "dashboard.sourceChart": "접수 채널", "dashboard.statusChart": "신고 상태", "dashboard.priorityChart": "우선순위 구성", "dashboard.timelineChart": "시간대별 신고",
    "dashboard.flow": "구조 진행 흐름", "dashboard.flowHint": "각 단계의 현재 신고 수", "dashboard.priorityList": "우선 사고", "dashboard.viewAll": "전체 보기",
    "dashboard.avgWait": "평균 대기", "dashboard.avgAssign": "팀 배정 시간", "dashboard.avgArrive": "현장 도착", "dashboard.avgComplete": "임무 완료",
    "dashboard.code": "코드", "dashboard.source": "출처", "dashboard.location": "위치", "dashboard.score": "점수", "dashboard.status": "상태", "dashboard.team": "팀",
    "dashboard.demoTitle": "짜린 급류 및 산사태", "dashboard.demoStart": "시뮬레이션 시작", "dashboard.next": "다음 이벤트", "dashboard.injectAll": "전체 주입", "dashboard.reset": "초기화",
    "requests.title": "긴급 신고", "requests.subtitle": "우선순위 대기열을 검색하고 필터링하여 처리합니다.", "teams.title": "구조팀", "teams.subtitle": "팀 역량을 확인하고 현장 임무를 엽니다.",
    "report.title": "구조 요청 보내기", "report.subtitle": "알고 있는 정보를 입력하세요. 인터넷이 끊겨도 신고는 기기에 저장됩니다.",
    "success.title": "요청이 접수되었습니다", "success.keepPhone": "연락할 수 있도록 휴대전화를 켜 두세요.", "success.another": "다른 요청 보내기",
    "form.online": "온라인", "form.offline": "오프라인", "form.name": "이름", "form.phone": "전화번호", "form.message": "긴급 요청 내용", "form.messageHint": "예: 5명이 고립되어 있고 물이 빠르게 차오르고 있습니다…", "form.address": "주소 또는 위치 설명", "form.people": "인원", "form.children": "어린이", "form.elderly": "노인", "form.injured": "부상자", "form.water": "예상 수위(미터)", "form.note": "추가 메모", "form.trapped": "고립됨", "form.disabled": "장애인 있음", "form.pregnant": "임산부 있음", "form.send": "SOS 보내기", "form.sending": "전송 중", "form.saveOffline": "기기에 SOS 저장", "form.localReports": "기기에 저장된 신고", "form.syncNow": "지금 동기화", "form.noQueue": "동기화 대기 신고가 없습니다.",
    "requests.search": "코드, 주소, 내용 검색", "requests.allSources": "모든 출처", "requests.allPriorities": "모든 우선순위", "requests.allStatuses": "모든 상태", "requests.allAssignments": "모든 배정", "requests.assigned": "배정됨", "requests.unassigned": "미배정", "requests.highest": "점수 높은 순", "requests.newest": "최신순", "requests.oldest": "오래된 순", "requests.recent": "최근 업데이트", "requests.time": "시간", "requests.people": "인원", "requests.wait": "대기", "requests.level": "등급", "requests.detail": "상세", "requests.previous": "이전", "requests.next": "다음", "requests.page": "페이지", "requests.empty": "일치하는 신고가 없습니다.",
    "teams.members": "명", "teams.openMission": "임무 열기", "teams.empty": "구조팀이 없습니다.", "mission.title": "구조팀 임무", "mission.subtitle": "현장 상태를 업데이트하여 지휘 센터에서 임무를 추적합니다.", "mission.empty": "이 팀에 배정된 임무가 없습니다.", "mission.contact": "연락처", "mission.address": "주소", "mission.people": "인원", "mission.injured": "부상자", "mission.note": "현장 메모",
    "detail.sender": "신고자", "detail.phone": "전화", "detail.address": "주소", "detail.people": "인원", "detail.children": "어린이", "detail.elderly": "노인", "detail.injured": "부상자", "detail.water": "수위", "detail.received": "접수 시간", "detail.unknown": "알 수 없음", "detail.missingLocation": "위치 정보 없음", "detail.priority": "우선순위 점수 설명", "detail.duplicates": "중복 의심 신고", "detail.confirm": "확인", "detail.reject": "거절", "detail.merge": "다음으로 병합", "detail.analysis": "AI 지원 분석", "detail.reanalyze": "다시 분석", "detail.noSummary": "요약 없음", "detail.risks": "감지된 위험", "detail.missing": "누락 정보", "detail.confidence": "신뢰도", "detail.none": "없음", "detail.timeline": "타임라인", "detail.noHistory": "기록 없음", "detail.recommendations": "추천 구조팀", "detail.noDistance": "거리 계산 불가", "detail.straightDistance": "km 직선거리", "detail.noVehicle": "차량 정보 없음", "detail.noTeam": "적합한 대기 팀이 없거나 위치 정보가 부족합니다.", "detail.assignment": "구조팀 배정", "detail.source": "출처", "detail.verify": "신고 확인", "detail.chooseTeam": "팀 선택", "detail.dispatchNote": "배정 메모", "detail.assign": "임무 배정", "detail.raw": "기술 JSON", "detail.openW3w": "What3words에서 위치 열기", "success.code": "요청 코드", "success.status": "상태", "success.missing": "제출한 요청 정보를 찾을 수 없습니다."
  }
};

type I18nContextValue = { language: Language; locale: string; setLanguage: (language: Language) => void; t: (key: string) => string };
const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem("sosflow-language");
    return saved === "en" || saved === "ko" ? saved : "vi";
  });
  useEffect(() => {
    localStorage.setItem("sosflow-language", language);
    document.documentElement.lang = language;
  }, [language]);
  const value = useMemo<I18nContextValue>(() => ({
    language,
    locale: language === "vi" ? "vi-VN" : language === "ko" ? "ko-KR" : "en-US",
    setLanguage,
    t: (key) => messages[language][key] ?? messages.vi[key] ?? key,
  }), [language]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside I18nProvider");
  return value;
}
