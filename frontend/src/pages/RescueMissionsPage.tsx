import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Mission } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";

const statuses = ["ACCEPTED", "MOVING", "ARRIVED", "RESCUING", "COMPLETED", "FAILED"];

export function RescueMissionsPage() {
  const { teamId = "" } = useParams();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [note, setNote] = useState<Record<number, string>>({});

  async function load() {
    const data = await api.getTeamMissions(teamId);
    setMissions(data);
  }

  useEffect(() => {
    load();
  }, [teamId]);

  async function update(missionId: number, status: string) {
    await api.updateMission(missionId, status, note[missionId]);
    await load();
  }

  const team = missions[0]?.team;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Nhiệm vụ đội cứu hộ {team ? `- ${team.name}` : `#${teamId}`}</h1>
        <p className="text-sm text-slate-600">Cập nhật trạng thái hiện trường để Command Center theo dõi vòng đời nhiệm vụ.</p>
      </div>
      {missions.length === 0 && <div className="rounded border border-slate-200 bg-white p-4">Đội này chưa có nhiệm vụ được giao.</div>}
      {missions.map((mission) => (
        <article key={mission.id} className="grid gap-4 rounded border border-slate-200 bg-white p-4 lg:grid-cols-[1fr_360px]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-bold">{mission.request.request_code}</h2>
              <PriorityBadge level={mission.request.priority_level} />
              <StatusBadge status={mission.status} />
            </div>
            <p className="font-semibold">{mission.request.message}</p>
            <div className="grid gap-2 text-sm md:grid-cols-2">
              <p><strong>Liên hệ:</strong> {mission.request.reporter_name ?? "Chưa rõ"} - {mission.request.phone_number ?? "Chưa có"}</p>
              <p><strong>Địa chỉ:</strong> {mission.request.address ?? "Thiếu vị trí"}</p>
              <p><strong>Số người:</strong> {mission.request.number_of_people}</p>
              <p><strong>Bị thương:</strong> {mission.request.number_of_injured}</p>
            </div>
            <textarea className="field min-h-20" placeholder="Ghi chú hiện trường" value={note[mission.id] ?? ""} onChange={(event) => setNote({ ...note, [mission.id]: event.target.value })} />
            <div className="flex flex-wrap gap-2">
              {statuses.map((status) => (
                <button key={status} onClick={() => update(mission.id, status)} className="rounded border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-100">{status}</button>
              ))}
            </div>
            {mission.notes && <div className="rounded bg-slate-50 p-3 text-sm"><strong>Ghi chú:</strong><br />{mission.notes}</div>}
          </div>
          <RequestMap requests={[mission.request]} />
        </article>
      ))}
    </div>
  );
}
