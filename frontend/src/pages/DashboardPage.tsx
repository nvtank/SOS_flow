import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, ChevronRight, Clock3, MapPin, RefreshCw, ShieldCheck, Users, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { api, DemoScenarioState, RescueRequest, RescueStation, RescueTeam, SilentZone, Statistics } from "../api/client";
import { DonutChart, HorizontalBars, TimelineChart } from "../components/DashboardCharts";
import { DuplicateBadge, PriorityBadge, SourceBadge, StatusBadge } from "../components/Badges";
import { MapArea, RequestMap } from "../components/RequestMap";
import { useI18n } from "../i18n";

const isDemo = import.meta.env.VITE_DEMO_MODE === "true";
const demoToken = import.meta.env.VITE_DEMO_TOKEN ?? "sosflow-demo";

export function DashboardPage() {
  const { locale, t } = useI18n();
  const [stats, setStats] = useState<Statistics>();
  const [requests, setRequests] = useState<RescueRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date>();
  const [zones, setZones] = useState<SilentZone[]>([]);
  const [stations, setStations] = useState<RescueStation[]>([]);
  const [teams, setTeams] = useState<RescueTeam[]>([]);
  const [mapArea, setMapArea] = useState<MapArea>(isDemo ? "TRA_LINH" : "DA_NANG");
  const [scenario, setScenario] = useState<DemoScenarioState>();
  const [demoMessage, setDemoMessage] = useState("");
  const [demoBusy, setDemoBusy] = useState(false);
  const demoInFlight = useRef(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const [nextStats, nextRequests, nextZones, nextStations, nextTeams] = await Promise.all([
        api.getStats(),
        api.getRequests("?page_size=100&sort_by=priority_score&sort_order=desc"),
        api.getSilentZones(true),
        api.getRescueStations(),
        api.getTeams(),
      ]);
      setStats(nextStats); setRequests(nextRequests.items); setZones(nextZones); setStations(nextStations); setTeams(nextTeams); setUpdatedAt(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load Command Center data.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    void load();
    if (!isDemo) return undefined;
    const timer = window.setInterval(() => void load(), 5_000);
    return () => window.clearInterval(timer);
  }, [load]);
  useEffect(() => { if (isDemo) api.demoStatus(demoToken).then(setScenario).catch(() => undefined); }, []);

  // Playback stays in the browser on purpose: every event still enters through
  // the protected API, while pause/unmount cancels the next scheduled call.
  useEffect(() => {
    if (!isDemo || !scenario || scenario.paused || scenario.complete) return undefined;
    const timer = window.setTimeout(async () => {
      if (demoInFlight.current) return;
      demoInFlight.current = true;
      setDemoBusy(true);
      try {
        const result = await api.demoNext(demoToken);
        setScenario(result);
        setDemoMessage(result.event ?? t("dashboard.demoTitle"));
        await load();
      } catch (cause) {
        setDemoMessage(cause instanceof Error ? cause.message : "Demo playback failed.");
        const latest = await api.demoStatus(demoToken).catch(() => undefined);
        if (latest) setScenario(latest);
      } finally {
        demoInFlight.current = false;
        setDemoBusy(false);
      }
    }, Math.max(750, 4_000 / scenario.speed));
    return () => window.clearTimeout(timer);
  }, [load, scenario, t]);

  async function control(action: "start" | "pause" | "speed" | "next" | "all" | "reset", speed = 1) {
    if (demoInFlight.current) return;
    demoInFlight.current = true;
    setDemoBusy(true);
    try {
      const result = action === "start" ? await api.demoStart(demoToken, speed)
        : action === "pause" ? await api.demoPause(demoToken, !scenario?.paused)
        : action === "speed" ? await api.demoSpeed(demoToken, speed)
        : action === "next" ? await api.demoNext(demoToken)
        : action === "all" ? await api.demoAll(demoToken)
        : await api.demoReset(demoToken);
      setScenario(result); setDemoMessage(result.event ? result.event : t("dashboard.demoTitle")); await load();
    } catch (cause) { setDemoMessage(cause instanceof Error ? cause.message : "Demo control failed."); }
    finally { demoInFlight.current = false; setDemoBusy(false); }
  }

  const missingLocation = useMemo(() => requests.filter((item) => item.latitude == null || item.longitude == null), [requests]);
  const timeSeries = stats?.requests_over_time_minutes.length ? stats.requests_over_time_minutes : stats?.requests_over_time ?? [];
  const kpis = stats ? [
    { label: t("dashboard.total"), hint: t("dashboard.totalHint"), value: stats.total_requests, icon: Activity, tone: "blue" },
    { label: t("dashboard.critical"), hint: t("dashboard.criticalHint"), value: stats.critical_requests, icon: Zap, tone: "red" },
    { label: t("dashboard.pending"), hint: t("dashboard.pendingHint"), value: stats.pending_verification, icon: Clock3, tone: "amber" },
    { label: t("dashboard.active"), hint: t("dashboard.activeHint"), value: stats.active_rescues, icon: ShieldCheck, tone: "purple" },
    { label: t("dashboard.completed"), hint: t("dashboard.completedHint"), value: stats.completed, icon: CheckCircle2, tone: "green" },
    { label: t("dashboard.available"), hint: t("dashboard.availableHint"), value: stats.available_teams, icon: Users, tone: "teal" },
  ] : [];

  return <div className="dashboard-shell">
    <header className="dashboard-header">
      <div><span className="eyebrow">SOSFLOW · LIVE OPERATIONS</span><h1>{t("dashboard.title")}</h1><p>{t("dashboard.subtitle")}</p></div>
      <div className="dashboard-refresh"><span>{updatedAt ? `${t("dashboard.updated")} ${updatedAt.toLocaleTimeString(locale)}` : "—"}{isDemo && <small>{t("dashboard.autoRefresh")}</small>}</span><button className="secondary-button" onClick={() => { setLoading(true); void load(); }}><RefreshCw size={16} className={loading ? "spin" : ""} />{t("common.refresh")}</button></div>
    </header>

    {error && <div className="inline-alert inline-alert--error"><AlertTriangle size={18} />{error}</div>}

    {isDemo && <section className="demo-control">
      <div className="demo-control__copy"><span className="demo-pulse"><i /> DEMO MODE</span><h2>{t("dashboard.demoTitle")}</h2><p>{scenario ? `${scenario.next_event}/${scenario.total_events} events · x${scenario.speed} · ${scenario.complete ? "Complete" : scenario.paused ? "Paused" : "Running"}` : t("common.loading")}</p></div>
      <div className="demo-control__actions"><button disabled={demoBusy} className="primary-button" onClick={() => void control("start", 1)}>{demoBusy ? "…" : t("dashboard.demoStart")}</button>{[1, 2, 5].map((speed) => <button disabled={demoBusy || !scenario} aria-pressed={scenario?.speed === speed} className={scenario?.speed === speed ? "active" : ""} key={speed} onClick={() => void control("speed", speed)}>x{speed}</button>)}<button disabled={demoBusy || !scenario || scenario.complete} onClick={() => void control("pause")}>{scenario?.paused ? "Resume" : "Pause"}</button><button disabled={demoBusy || !scenario || scenario.complete} onClick={() => void control("next")}>{t("dashboard.next")}</button><button disabled={demoBusy || !scenario || scenario.complete} onClick={() => void control("all")}>{t("dashboard.injectAll")}</button><button disabled={demoBusy} onClick={() => void control("reset")}>{t("dashboard.reset")}</button></div>
      {demoMessage && <div className="demo-message">{demoMessage}</div>}
    </section>}

    <section className="kpi-grid" aria-label="Key metrics">
      {kpis.map(({ label, hint, value, icon: Icon, tone }) => <article key={label} className={`kpi-card kpi-card--${tone}`}><div className="kpi-card__icon"><Icon size={20} /></div><div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div></article>)}
      {loading && !stats && Array.from({ length: 6 }, (_, index) => <div className="kpi-card skeleton" key={index} />)}
    </section>

    <section className="workflow-card">
      <div className="card-heading"><div><h2>{t("dashboard.flow")}</h2><p>{t("dashboard.flowHint")}</p></div></div>
      <div className="workflow-track">
        <FlowStep label="PENDING" value={stats?.pending_verification ?? 0} tone="amber" />
        <ChevronRight />
        <FlowStep label="VERIFIED" value={stats?.verified ?? 0} tone="blue" />
        <ChevronRight />
        <FlowStep label="ASSIGNED" value={stats?.assigned ?? 0} tone="purple" />
        <ChevronRight />
        <FlowStep label="IN RESCUE" value={stats?.active_rescues ?? 0} tone="red" />
        <ChevronRight />
        <FlowStep label="COMPLETED" value={stats?.completed ?? 0} tone="green" />
      </div>
    </section>

    <div className="dashboard-primary-grid">
      <section className="dashboard-card map-card">
        <div className="card-heading"><div><h2>{t("dashboard.map")}</h2><p>{t("dashboard.mapHint")} · Trạm là điểm cố định; nét đứt là khoảng cách đường thẳng.</p></div><div className="map-legend"><span><i className="critical" />Critical</span><span><i className="high" />High</span><span><i className="normal" />Normal</span></div></div>
        <div className="map-region-tabs" role="group" aria-label="Map area">
          {(["TRA_LINH", "DA_NANG", "ALL"] as MapArea[]).map((area) => <button key={area} onClick={() => setMapArea(area)} className={mapArea === area ? "active" : ""}>{area === "TRA_LINH" ? "Trà Linh" : area === "DA_NANG" ? "Đà Nẵng" : "Tất cả"}</button>)}
        </div>
        <RequestMap requests={requests} zones={zones} stations={stations} teams={teams} area={mapArea} showAssignedConnections className="dashboard-map" />
      </section>
      <ActionPanel stats={stats} zones={zones} missingLocation={missingLocation} load={load} />
    </div>

    <div className="chart-grid">
      <DonutChart title={t("dashboard.priorityChart")} data={stats?.requests_by_priority ?? []} centerLabel="reports" />
      <HorizontalBars title={t("dashboard.sourceChart")} data={stats?.requests_by_source ?? []} />
      <HorizontalBars title={t("dashboard.statusChart")} data={stats?.requests_by_status ?? []} />
    </div>
    <TimelineChart title={t("dashboard.timelineChart")} data={timeSeries} locale={locale} />

    <section className="dashboard-card priority-table-card">
      <div className="card-heading"><div><h2>{t("dashboard.priorityList")}</h2><p>Top 10 · priority score</p></div><Link to="/admin/requests">{t("dashboard.viewAll")} <ChevronRight size={16} /></Link></div>
      <div className="table-scroll"><table className="operations-table"><thead><tr><th>{t("dashboard.code")}</th><th>{t("dashboard.source")}</th><th>{t("dashboard.location")}</th><th>{t("dashboard.score")}</th><th>{t("dashboard.status")}</th><th>{t("dashboard.team")}</th><th /></tr></thead><tbody>
        {requests.slice(0, 10).map((item) => <tr key={item.id}><td><Link className="request-code" to={`/admin/requests/${item.id}`}>{item.request_code}</Link><small>{new Date(item.received_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}</small></td><td><SourceBadge source={item.source} /> <DuplicateBadge state={item.duplicate_state} />{item.source === "OFFLINE_SYNC" && <small>{syncDelay(item, locale)}</small>}</td><td><span className={!item.address ? "missing-value" : ""}>{item.address ?? t("dashboard.missingLocation")}</span></td><td><strong className="score-value">{item.priority_score}</strong><PriorityBadge level={item.priority_level} /></td><td><StatusBadge status={item.status} /></td><td>{item.assigned_team?.name ?? "—"}</td><td><Link className="row-action" to={`/admin/requests/${item.id}`} aria-label={t("common.open")}><ChevronRight size={18} /></Link></td></tr>)}
        {!requests.length && <tr><td colSpan={7} className="empty-table">{t("common.noData")}</td></tr>}
      </tbody></table></div>
    </section>

    <section className="metric-strip"><Metric label={t("dashboard.avgWait")} value={`${stats?.average_waiting_minutes ?? 0} min`} /><Metric label={t("dashboard.avgAssign")} value={formatMinutes(stats?.average_time_to_assign)} /><Metric label={t("dashboard.avgArrive")} value={formatMinutes(stats?.average_time_to_arrive)} /><Metric label={t("dashboard.avgComplete")} value={formatMinutes(stats?.average_completion_time)} /></section>
  </div>;
}

function ActionPanel({ stats, zones, missingLocation, load }: { stats?: Statistics; zones: SilentZone[]; missingLocation: RescueRequest[]; load: () => Promise<void> }) {
  const { t } = useI18n();
  return <section className="dashboard-card action-panel">
    <div className="card-heading"><div><h2>{t("dashboard.actions")}</h2><p>{(stats?.action_alerts ?? []).reduce((sum, alert) => sum + alert.count, 0)} open alerts</p></div><AlertTriangle size={20} /></div>
    <div className="action-list">{stats?.action_alerts.length ? stats.action_alerts.map((alert) => <div className={`action-item action-item--${alert.severity.toLowerCase()}`} key={alert.key}><span><i /><strong>{alert.label}</strong></span><b>{alert.count}</b></div>) : <div className="empty-action"><CheckCircle2 size={24} /><span>{t("dashboard.noAlerts")}</span></div>}</div>
    <div className="panel-section"><h3>{t("dashboard.silentZones")} <span>{zones.length}</span></h3>{zones.slice(0, 3).map((zone) => <div className="zone-item" key={zone.id}><div><strong>{zone.name}</strong><small>{zone.silence_minutes == null ? "No report" : `${Math.round(zone.silence_minutes)} min silence`}</small></div><div><button onClick={() => api.updateSilentZone(zone.id, "VERIFYING", "Operator verifying").then(load)}>Verify</button><button onClick={() => api.updateSilentZone(zone.id, "SAFE", "Confirmed safe").then(load)}>Safe</button></div></div>)}{!zones.length && <p className="panel-empty">{t("common.noData")}</p>}</div>
    <div className="panel-section"><h3>{t("dashboard.missingLocation")} <span>{missingLocation.length}</span></h3>{missingLocation.slice(0, 4).map((item) => <Link className="location-item" to={`/admin/requests/${item.id}`} key={item.id}><MapPin size={15} /><span>{item.request_code}<small>{item.source}</small></span><ChevronRight size={15} /></Link>)}{!missingLocation.length && <p className="panel-empty">{t("common.noData")}</p>}</div>
  </section>;
}

function FlowStep({ label, value, tone }: { label: string; value: number; tone: string }) { return <div className={`flow-step flow-step--${tone}`}><span>{label}</span><strong>{value}</strong></div>; }
function Metric({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function formatMinutes(value?: number) { return value == null ? "—" : `${value} min`; }
function syncDelay(request: RescueRequest, locale: string) { const minutes = Math.max(0, Math.round((new Date(request.synced_at).getTime() - new Date(request.received_at).getTime()) / 60_000)); return new Intl.NumberFormat(locale).format(minutes) + " min delay"; }
