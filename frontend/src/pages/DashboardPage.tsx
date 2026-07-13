import { useEffect, useState } from "react";
import { Activity, AlertOctagon, CheckCircle2, Clock, ShieldCheck, Users } from "lucide-react";
import { api, RescueRequest, Statistics } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";

const statIcons = [ClipboardIcon, AlertOctagon, Clock, Activity, CheckCircle2, ShieldCheck];

function ClipboardIcon(props: { size?: number }) {
  return <Users {...props} />;
}

export function DashboardPage() {
  const [stats, setStats] = useState<Statistics>();
  const [requests, setRequests] = useState<RescueRequest[]>([]);

  useEffect(() => {
    api.getStats().then(setStats);
    api.getRequests().then(setRequests);
  }, []);

  const items = stats
    ? [
        ["Tổng yêu cầu", stats.total_requests],
        ["Nguy cấp", stats.critical_requests],
        ["Chờ xử lý", stats.pending_requests],
        ["Đang cứu hộ", stats.active_rescues],
        ["Hoàn thành", stats.completed_requests],
        ["Đội sẵn sàng", stats.available_teams],
      ]
    : [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Command Center Dashboard</h1>
        <p className="text-sm text-slate-600">Theo dõi tiếp nhận, ưu tiên và điều phối cứu hộ theo thời gian gần thực.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {items.map(([label, value], index) => {
          const Icon = statIcons[index];
          return (
            <div key={label} className="rounded border border-slate-200 bg-white p-4">
              <Icon size={18} />
              <div className="mt-3 text-2xl font-bold">{value}</div>
              <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
            </div>
          );
        })}
      </div>
      <RequestMap requests={requests} />
      <div className="overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">Mã</th>
              <th className="px-3 py-2">Người gửi</th>
              <th className="px-3 py-2">Vị trí</th>
              <th className="px-3 py-2">Điểm</th>
              <th className="px-3 py-2">Ưu tiên</th>
              <th className="px-3 py-2">Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {requests.slice(0, 8).map((item) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-semibold">{item.request_code}</td>
                <td className="px-3 py-2">{item.reporter_name ?? "Chưa rõ"}</td>
                <td className="px-3 py-2">{item.address ?? "Thiếu vị trí"}</td>
                <td className="px-3 py-2 font-bold">{item.priority_score}</td>
                <td className="px-3 py-2"><PriorityBadge level={item.priority_level} /></td>
                <td className="px-3 py-2"><StatusBadge status={item.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
