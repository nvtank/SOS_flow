import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, RescueRequest, RescueTeam } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";

export function RequestDetailPage() {
  const { id = "" } = useParams();
  const [request, setRequest] = useState<RescueRequest>();
  const [teams, setTeams] = useState<RescueTeam[]>([]);
  const [teamId, setTeamId] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.getRequest(id).then(setRequest);
    api.getTeams().then(setTeams);
  }, [id]);

  async function assign() {
    if (!request || !teamId) return;
    await api.assign(request.id, Number(teamId), note);
    const updated = await api.getRequest(id);
    setRequest(updated);
    setMessage("Đã phân công nhiệm vụ.");
  }

  if (!request) return <div>Đang tải...</div>;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="space-y-4 rounded border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{request.request_code}</h1>
          <PriorityBadge level={request.priority_level} />
          <StatusBadge status={request.status} />
        </div>
        <p className="text-lg font-semibold">{request.message}</p>
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <Info label="Người gửi" value={request.reporter_name ?? "Chưa rõ"} />
          <Info label="Điện thoại" value={request.phone_number ?? "Chưa có"} />
          <Info label="Địa chỉ" value={request.address ?? "Thiếu vị trí"} />
          <Info label="Số người" value={`${request.number_of_people}`} />
          <Info label="Trẻ em" value={`${request.number_of_children}`} />
          <Info label="Người cao tuổi" value={`${request.number_of_elderly}`} />
          <Info label="Bị thương" value={`${request.number_of_injured}`} />
          <Info label="Mực nước" value={request.water_level ? `${request.water_level} m` : "Chưa rõ"} />
        </div>
        <div>
          <h2 className="mb-2 font-bold">Giải thích điểm ưu tiên: {request.priority_score}</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {request.priority_reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
        <div>
          <h2 className="mb-2 font-bold">Phân tích AI mock</h2>
          <pre className="overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(request.ai_analysis, null, 2)}</pre>
        </div>
      </section>
      <aside className="space-y-4">
        <RequestMap requests={[request]} />
        <div className="rounded border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-bold">Phân công đội cứu hộ</h2>
          <div className="space-y-3">
            <select className="field" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              <option value="">Chọn đội</option>
              {teams.map((team) => <option key={team.id} value={team.id}>{team.name} - {team.status}</option>)}
            </select>
            <textarea className="field min-h-20" placeholder="Ghi chú điều phối" value={note} onChange={(event) => setNote(event.target.value)} />
            <button onClick={assign} className="rounded bg-command px-4 py-2 font-semibold text-white">Giao nhiệm vụ</button>
            {message && <p className="text-sm text-green-700">{message}</p>}
          </div>
        </div>
      </aside>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><div className="label">{label}</div><div className="font-medium">{value}</div></div>;
}
