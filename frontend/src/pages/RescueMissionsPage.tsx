import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Mission, MissionEvent } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";
import { useI18n } from "../i18n";

const allowedNext: Record<string, string[]> = {
  ASSIGNED: ["ACCEPTED"], ACCEPTED: ["MOVING"], MOVING: ["ARRIVED", "BLOCKED"],
  BLOCKED: ["MOVING", "FAILED"], ARRIVED: ["RESCUING", "NEED_REINFORCEMENT"],
  RESCUING: ["COMPLETED", "FAILED", "NEED_REINFORCEMENT"], NEED_REINFORCEMENT: ["RESCUING", "FAILED"],
  COMPLETED: [], FAILED: [],
};

export function RescueMissionsPage() {
  const { t } = useI18n();
  const { teamId = "" } = useParams();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [note, setNote] = useState<Record<number, string>>({});
  const [events, setEvents] = useState<Record<number, MissionEvent[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMissionId, setActionMissionId] = useState<number>();
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const data = await api.getTeamMissions(teamId);
      const histories = await Promise.all(data.map(async (mission) => [mission.id, await api.getMissionEvents(mission.id)] as const));
      setMissions(data); setEvents(Object.fromEntries(histories));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể tải nhiệm vụ."); }
    finally { setLoading(false); }
  }, [teamId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function update(missionId: number, status: string) {
    try {
      setActionMissionId(missionId); setError(""); setSuccess("");
      await api.updateMission(missionId, status, note[missionId]);
      setSuccess(`Nhiệm vụ #${missionId} đã chuyển sang ${status}.`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể cập nhật nhiệm vụ."); }
    finally { setActionMissionId(undefined); }
  }

  const team = missions[0]?.team;

  return (
    <div className="space-y-8">
      <div className="apple-page-head">
        <h1>{t("mission.title")} {team ? `- ${team.name}` : `#${teamId}`}</h1>
        <p>{t("mission.subtitle")}</p>
      </div>
      {error && <div className="rounded border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {success && <div className="rounded border border-green-200 bg-green-50 p-4 text-green-800">{success}</div>}
      {loading && <div className="apple-utility-card">{t("common.loading")}</div>}
      {!loading && missions.length === 0 && <div className="apple-utility-card">{t("mission.empty")}</div>}
      {missions.map((mission) => (
        <article key={mission.id} className="apple-utility-card grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <Link to={`/admin/requests/${mission.request.id}`} className="text-[28px] font-semibold tracking-[-0.28px] text-[#0066cc]">{mission.request.request_code}</Link>
              <PriorityBadge level={mission.request.priority_level} />
              <StatusBadge status={mission.status} />
            </div>
            <p className="font-semibold">{mission.request.message}</p>
            <div className="grid gap-2 text-sm md:grid-cols-2">
              <p><strong>{t("mission.contact")}:</strong> {mission.request.reporter_name ?? "—"} - {mission.request.phone_number ?? "—"}</p>
              <p><strong>{t("mission.address")}:</strong> {mission.request.address ?? "—"}</p>
              <p><strong>{t("mission.people")}:</strong> {mission.request.number_of_people}</p>
              <p><strong>{t("mission.injured")}:</strong> {mission.request.number_of_injured}</p>
            </div>
            <textarea className="field min-h-20" placeholder={t("mission.note")} value={note[mission.id] ?? ""} onChange={(event) => setNote({ ...note, [mission.id]: event.target.value })} />
            <div className="flex flex-wrap gap-2">
              {(allowedNext[mission.status] ?? []).map((status) => (
                <button disabled={actionMissionId === mission.id} key={status} onClick={() => void update(mission.id, status)} className="apple-action apple-action--secondary apple-action--small disabled:opacity-50">{status}</button>
              ))}
              {(allowedNext[mission.status] ?? []).length === 0 && <span className="text-sm text-slate-500">Nhiệm vụ đã kết thúc, không còn bước chuyển trạng thái.</span>}
            </div>
            {mission.notes && <div className="border-t border-[#e0e0e0] pt-3 text-sm"><strong>Ghi chú:</strong><br />{mission.notes}</div>}
            <div className="border-t border-[#e0e0e0] pt-3 text-sm"><strong>Nhật ký nhiệm vụ</strong><ol className="mt-2 space-y-2 border-l border-slate-200 pl-4">{(events[mission.id] ?? []).map((event) => <li key={event.id}><div className="font-semibold">{event.event_type} <span className="font-normal text-slate-500">· {event.actor}</span></div><div className="text-slate-500">{new Date(event.created_at).toLocaleString()}{event.note ? ` · ${event.note}` : ""}</div></li>)}</ol></div>
          </div>
          <RequestMap requests={[mission.request]} />
        </article>
      ))}
    </div>
  );
}
