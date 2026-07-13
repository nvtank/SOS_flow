import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { api, RescueRequest } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";

export function RequestsPage() {
  const [requests, setRequests] = useState<RescueRequest[]>([]);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (priority) params.set("priority_level", priority);
    if (search) params.set("search", search);
    const text = params.toString();
    return text ? `?${text}` : "";
  }, [status, priority, search]);

  useEffect(() => {
    api.getRequests(query).then(setRequests);
  }, [query]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Danh sách yêu cầu</h1>
          <p className="text-sm text-slate-600">Mặc định sắp xếp theo điểm ưu tiên từ cao xuống thấp.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="relative">
            <Search className="absolute left-2 top-2.5 text-slate-400" size={16} />
            <input className="field pl-8" placeholder="Tìm kiếm" value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <select className="field w-40" value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">Mọi ưu tiên</option>
            <option>CRITICAL</option>
            <option>HIGH</option>
            <option>MEDIUM</option>
            <option>LOW</option>
          </select>
          <select className="field w-48" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Mọi trạng thái</option>
            <option>PENDING_VERIFICATION</option>
            <option>ASSIGNED</option>
            <option>ACCEPTED</option>
            <option>MOVING</option>
            <option>ARRIVED</option>
            <option>RESCUING</option>
            <option>COMPLETED</option>
            <option>FAILED</option>
          </select>
        </div>
      </div>
      <div className="overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="min-w-[980px] w-full text-sm">
          <thead className="bg-slate-100 text-left text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">Mã</th>
              <th className="px-3 py-2">Thời gian</th>
              <th className="px-3 py-2">Người gửi</th>
              <th className="px-3 py-2">Vị trí</th>
              <th className="px-3 py-2">Số người</th>
              <th className="px-3 py-2">Điểm</th>
              <th className="px-3 py-2">Mức</th>
              <th className="px-3 py-2">Trạng thái</th>
              <th className="px-3 py-2">Đội</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {requests.map((item) => (
              <tr key={item.id} className="border-t border-slate-100 align-top">
                <td className="px-3 py-2 font-semibold">{item.request_code}</td>
                <td className="px-3 py-2">{new Date(item.created_at).toLocaleString("vi-VN")}</td>
                <td className="px-3 py-2">{item.reporter_name ?? "Chưa rõ"}</td>
                <td className="px-3 py-2">{item.address ?? "Thiếu vị trí"}</td>
                <td className="px-3 py-2">{item.number_of_people}</td>
                <td className="px-3 py-2 font-bold">{item.priority_score}</td>
                <td className="px-3 py-2"><PriorityBadge level={item.priority_level} /></td>
                <td className="px-3 py-2"><StatusBadge status={item.status} /></td>
                <td className="px-3 py-2">{item.assigned_team?.name ?? "-"}</td>
                <td className="px-3 py-2"><Link className="font-semibold text-sky-700" to={`/admin/requests/${item.id}`}>Chi tiết</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
