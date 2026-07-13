import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, RescueTeam } from "../api/client";

export function TeamsPage() {
  const [teams, setTeams] = useState<RescueTeam[]>([]);

  useEffect(() => {
    api.getTeams().then(setTeams);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Đội cứu hộ</h1>
        <p className="text-sm text-slate-600">MVP dùng đăng nhập giả lập. Chọn một đội để xem nhiệm vụ.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {teams.map((team) => (
          <article key={team.id} className="rounded border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-bold">{team.name}</h2>
              <span className={`status-pill ${team.status === "AVAILABLE" ? "bg-green-100 text-green-800" : team.status === "BUSY" ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-700"}`}>{team.status}</span>
            </div>
            <div className="mt-3 space-y-1 text-sm text-slate-700">
              <p>{team.phone_number}</p>
              <p>{team.member_count} thành viên</p>
              <p>{team.vehicle_type}</p>
            </div>
            <Link to={`/rescue/${team.id}/missions`} className="mt-4 inline-block rounded bg-command px-3 py-2 text-sm font-semibold text-white">Mở nhiệm vụ</Link>
          </article>
        ))}
      </div>
    </div>
  );
}
