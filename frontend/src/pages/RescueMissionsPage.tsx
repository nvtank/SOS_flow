import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Mission } from "../api/client";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";
import { useI18n } from "../i18n";

const statuses = ["ACCEPTED", "MOVING", "BLOCKED", "ARRIVED", "RESCUING", "NEED_REINFORCEMENT", "COMPLETED", "FAILED"];

export function RescueMissionsPage() {
  const { t } = useI18n();
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
    <div className="space-y-8">
      <div className="apple-page-head">
        <h1>{t("mission.title")} {team ? `- ${team.name}` : `#${teamId}`}</h1>
        <p>{t("mission.subtitle")}</p>
      </div>
      {missions.length === 0 && <div className="apple-utility-card">{t("mission.empty")}</div>}
      {missions.map((mission) => (
        <article key={mission.id} className="apple-utility-card grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-[28px] font-semibold tracking-[-0.28px]">{mission.request.request_code}</h2>
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
              {statuses.map((status) => (
                <button key={status} onClick={() => update(mission.id, status)} className="apple-action apple-action--secondary apple-action--small">{status}</button>
              ))}
            </div>
            {mission.notes && <div className="border-t border-[#e0e0e0] pt-3 text-sm"><strong>Ghi chú:</strong><br />{mission.notes}</div>}
          </div>
          <RequestMap requests={[mission.request]} />
        </article>
      ))}
    </div>
  );
}
