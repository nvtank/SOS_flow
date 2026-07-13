export function PriorityBadge({ level }: { level: string }) {
  const classes: Record<string, string> = {
    CRITICAL: "bg-red-100 text-critical",
    HIGH: "bg-orange-100 text-high",
    MEDIUM: "bg-yellow-100 text-medium",
    LOW: "bg-green-100 text-low",
  };
  return <span className={`status-pill ${classes[level] ?? "bg-slate-100 text-slate-700"}`}>{level}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const active = ["ASSIGNED", "ACCEPTED", "MOVING", "ARRIVED", "RESCUING"].includes(status);
  const done = status === "COMPLETED";
  return <span className={`status-pill ${done ? "bg-green-100 text-green-800" : active ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-700"}`}>{status}</span>;
}
