import { useI18n } from "../i18n";

export function PriorityBadge({ level }: { level: string }) {
  const classes: Record<string, string> = {
    CRITICAL: "bg-slate-100 text-command",
    HIGH: "bg-slate-100 text-command",
    MEDIUM: "bg-slate-100 text-command",
    LOW: "bg-slate-100 text-command",
  };
  return <span className={`status-pill ${classes[level] ?? "bg-slate-100 text-slate-700"}`}>{level}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const active = ["ASSIGNED", "ACCEPTED", "MOVING", "BLOCKED", "ARRIVED", "RESCUING", "NEED_REINFORCEMENT"].includes(status);
  const done = status === "COMPLETED";
  return <span className={`status-pill ${done ? "bg-slate-100 text-command" : active ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-700"}`}>{status}</span>;
}

export function SourceBadge({ source }: { source: string }) {
  const { language } = useI18n();
  const labels: Record<string, Record<string, string>> = {
    vi: { CALL_112: "112 (mô phỏng)", LOCAL_OFFICER: "Cán bộ", OFFLINE_SYNC: "Đồng bộ offline", SOCIAL_MEDIA: "Mạng xã hội" },
    en: { CALL_112: "112 (sim)", LOCAL_OFFICER: "Local officer", OFFLINE_SYNC: "Offline sync", SOCIAL_MEDIA: "Social media" },
    ko: { CALL_112: "112 (모의)", LOCAL_OFFICER: "지역 담당자", OFFLINE_SYNC: "오프라인 동기화", SOCIAL_MEDIA: "소셜 미디어" },
  };
  return <span className="status-pill bg-slate-100 text-command">{labels[language][source] ?? source}</span>;
}

export function DuplicateBadge({ state }: { state: string }) {
  const { language } = useI18n();
  const possible = { vi: "Nghi trùng", en: "Possible duplicate", ko: "중복 의심" }[language];
  const confirmed = { vi: "Đã xác nhận trùng", en: "Duplicate confirmed", ko: "중복 확인" }[language];
  if (state === "POSSIBLE_DUPLICATE") return <span className="status-pill bg-slate-100 text-command">{possible}</span>;
  if (state === "CONFIRMED_DUPLICATE") return <span className="status-pill bg-slate-100 text-command">{confirmed}</span>;
  return null;
}
