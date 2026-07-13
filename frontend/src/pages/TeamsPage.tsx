import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, RescueTeam } from "../api/client";
import { useI18n } from "../i18n";

export function TeamsPage() {
  const { t } = useI18n();
  const [teams, setTeams] = useState<RescueTeam[]>([]);

  useEffect(() => {
    api.getTeams().then(setTeams);
  }, []);

  return (
    <div className="space-y-8">
      <div className="dashboard-header">
        <div><span className="eyebrow">SOSFLOW · FIELD UNITS</span><h1>{t("teams.title")}</h1><p>{t("teams.subtitle")}</p></div>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {teams.map((team) => (
          <article key={team.id} className="apple-utility-card">
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-[21px] font-semibold tracking-[-0.2px]">{team.name}</h2>
              <span className={`status-pill ${team.status === "AVAILABLE" ? "bg-green-100 text-green-800" : team.status === "BUSY" ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-700"}`}>{team.status}</span>
            </div>
            <div className="mt-4 space-y-1 text-[15px] text-[#333]">
              <p>{team.phone_number}</p>
              <p>{team.member_count} {t("teams.members")}</p>
              <p>{team.vehicle_type}</p>
            </div>
            <Link to={`/rescue/${team.id}/missions`} className="primary-button mt-5 inline-flex">{t("teams.openMission")}</Link>
          </article>
        ))}
        {!teams.length && <div className="apple-utility-card">{t("teams.empty")}</div>}
      </div>
    </div>
  );
}
