import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, DuplicateCandidate, DuplicateSummary, RescueRequest, RescueStation, RescueTeam, StatusHistory, TeamRecommendation } from "../api/client";
import { DuplicateBadge, PriorityBadge, SourceBadge, StatusBadge } from "../components/Badges";
import { RequestMap } from "../components/RequestMap";
import { useI18n } from "../i18n";

export function RequestDetailPage() {
  const { locale, t } = useI18n();
  const { id = "" } = useParams();
  const [request, setRequest] = useState<RescueRequest>();
  const [teams, setTeams] = useState<RescueTeam[]>([]);
  const [stations, setStations] = useState<RescueStation[]>([]);
  const [teamId, setTeamId] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [duplicateSummary, setDuplicateSummary] = useState<DuplicateSummary>();
  const [timeline, setTimeline] = useState<StatusHistory[]>([]);
  const [showTechnical, setShowTechnical] = useState(false);
  const [recommendations, setRecommendations] = useState<TeamRecommendation[]>([]);
  const [actionError, setActionError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [editingFacts, setEditingFacts] = useState(false);
  const isDemo = import.meta.env.VITE_DEMO_MODE === "true";

  const refresh = useCallback(async () => {
    try {
      setActionError("");
      const [loadedRequest, loadedTeams, loadedStations, loadedCandidates, loadedDuplicateSummary, loadedTimeline, loadedRecommendations] = await Promise.all([
        api.getRequest(id), api.getTeams(), api.getRescueStations(), api.getDuplicates(Number(id)), api.getDuplicateSummary(Number(id)), api.getTimeline(Number(id)), api.getTeamRecommendations(Number(id)),
      ]);
      setRequest(loadedRequest); setTeams(loadedTeams); setStations(loadedStations); setCandidates(loadedCandidates); setDuplicateSummary(loadedDuplicateSummary); setTimeline(loadedTimeline); setRecommendations(loadedRecommendations);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Không thể tải chi tiết yêu cầu.");
    }
  }, [id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runAction(action: () => Promise<void>) {
    try { setActionLoading(true); setActionError(""); await action(); }
    catch (error) { setActionError(error instanceof Error ? error.message : "Thao tác không thể hoàn tất."); }
    finally { setActionLoading(false); }
  }

  async function assign() {
    if (!request || !teamId) { setActionError("Chọn một đội AVAILABLE trước khi giao nhiệm vụ."); return; }
    await runAction(async () => { await api.assign(request.id, Number(teamId), note); await refresh(); setMessage("Đã phân công nhiệm vụ."); });
  }

  async function decide(candidate: DuplicateCandidate, confirmed: boolean) {
    if (!request) return;
    await runAction(async () => {
      const updated = confirmed
        ? await api.confirmDuplicate(request.id, candidate.id, note)
        : await api.rejectDuplicate(request.id, candidate.id, note);
      setCandidates((items) => items.map((item) => item.id === updated.id ? updated : item));
      await refresh();
      setMessage(confirmed ? "Đã xác nhận nghi vấn trùng. Có thể gộp báo cáo sau khi kiểm tra." : "Đã từ chối đề xuất trùng.");
    });
  }

  async function merge(candidate: DuplicateCandidate) {
    if (!request) return;
    await runAction(async () => {
      await api.mergeDuplicate(request.id, candidate.id, candidate.candidate_request_id, note);
      await refresh();
      setMessage(`Đã giữ báo cáo gốc và gộp vào incident ${candidate.candidate_request.request_code}.`);
    });
  }

  async function verify() {
    if (!request) return;
    await runAction(async () => { await api.updateRequest(request.id, { status: "VERIFIED", note: "Đã xác minh bởi điều phối viên" }); await refresh(); setMessage("Yêu cầu đã được xác minh và sẵn sàng phân công."); });
  }

  async function reanalyze() {
    if (!request) return;
    await runAction(async () => { await api.reanalyze(request.id); await refresh(); setMessage("Đã tạo preview AI mới; dữ liệu người báo không bị thay đổi."); });
  }

  async function saveFacts(values: Record<string, unknown>) {
    if (!request) return;
    await runAction(async () => {
      await api.updateRequest(request.id, { ...values, note: "Điều phối viên cập nhật dữ liệu đã xác minh" });
      await refresh(); setEditingFacts(false);
      setMessage("Đã lưu dữ liệu, chạy lại phân tích và tính lại điểm ưu tiên.");
    });
  }

  if (!request) return <div>Đang tải...</div>;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="apple-utility-card space-y-5">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[34px] font-semibold tracking-[-0.374px]">{request.request_code}</h1>
          <PriorityBadge level={request.priority_level} />
          <SourceBadge source={request.source} />
          <DuplicateBadge state={request.duplicate_state} />
          <StatusBadge status={request.status} />
        </div>
        <p className="text-[21px] font-semibold tracking-[-0.28px]">{request.message}</p>
        {typeof request.raw_payload?.what3words_url === "string" && <a className="inline-block text-sm font-semibold text-sky-700" href={request.raw_payload.what3words_url} target="_blank" rel="noreferrer">{t("detail.openW3w")}</a>}
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <Info label={t("detail.sender")} value={request.reporter_name ?? t("detail.unknown")} />
          <Info label={t("detail.phone")} value={request.phone_number ?? t("detail.unknown")} />
          <Info label={t("detail.address")} value={request.address ?? t("detail.missingLocation")} />
          <Info label={t("detail.people")} value={`${request.number_of_people}`} />
          <Info label={t("detail.children")} value={`${request.number_of_children}`} />
          <Info label={t("detail.elderly")} value={`${request.number_of_elderly}`} />
          <Info label={t("detail.injured")} value={`${request.number_of_injured}`} />
          <Info label={t("detail.water")} value={request.water_level ? `${request.water_level} m` : t("detail.unknown")} />
          <Info label={t("detail.received")} value={new Date(request.received_at).toLocaleString(locale)} />
        </div>
        <div className="border-t border-[#e0e0e0] pt-4">
          <button className="secondary-button" onClick={() => setEditingFacts((value) => !value)}>{editingFacts ? "Đóng chỉnh sửa" : "Chỉnh dữ liệu đã xác minh"}</button>
          {editingFacts && <VerifiedFactsForm request={request} loading={actionLoading} onCancel={() => setEditingFacts(false)} onSave={saveFacts} />}
        </div>
        <div>
          <h2 className="mb-2 font-bold">{t("detail.priority")}: {request.priority_score}</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {request.priority_reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
        {(duplicateSummary?.merged_report_count ?? 0) > 0 && <div className="rounded border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900"><strong>Incident chính có {duplicateSummary?.merged_report_count} báo cáo đã gộp.</strong> Báo cáo gốc vẫn được giữ để kiểm tra audit.</div>}
        {request.canonical_request_id && <div className="rounded border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">Báo cáo này đã gộp vào incident chính <a className="font-semibold underline" href={`/admin/requests/${request.canonical_request_id}`}>#{request.canonical_request_id}</a>; dữ liệu gốc không bị xóa.</div>}
        {candidates.length > 0 && <div className="rounded border border-amber-200 bg-amber-50 p-3">
          <h2 className="mb-2 font-bold text-amber-900">{t("detail.duplicates")}</h2>
          <div className="space-y-3">
            {candidates.map((candidate) => <div key={candidate.id} className="rounded border border-amber-200 bg-white p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2 font-semibold"><DuplicateBadge state={candidate.status} /> {candidate.candidate_request.request_code} · {Math.round(candidate.duplicate_score * 100)}%</div>
              <p className="mt-1">{candidate.candidate_request.message}</p>
              <ul className="mt-2 list-disc pl-5">{candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
              {candidate.status === "POSSIBLE_DUPLICATE" && <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={() => decide(candidate, true)} className="primary-button">{t("detail.confirm")}</button>
                <button onClick={() => decide(candidate, false)} className="secondary-button">{t("detail.reject")}</button>
              </div>}
              {candidate.status === "CONFIRMED_DUPLICATE" && !request.canonical_request_id && <button onClick={() => merge(candidate)} className="primary-button mt-3">{t("detail.merge")} {candidate.candidate_request.request_code}</button>}
            </div>)}
          </div>
        </div>}
        <div className="apple-tile apple-tile--paper p-6"><div className="flex flex-wrap items-center justify-between gap-2"><div><span className={`mb-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${request.intake_mode === "STRUCTURED" ? "bg-slate-200 text-slate-800" : request.ai_metadata.bedrock_succeeded ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>{request.intake_mode === "STRUCTURED" ? "RULE-BASED · NO AI" : request.ai_metadata.bedrock_succeeded ? "AMAZON BEDROCK · SUCCESS" : "AI FALLBACK"}</span><h2 className="text-[21px] font-semibold tracking-[-0.28px]">{request.intake_mode === "STRUCTURED" ? "Phân tích dữ liệu cố định" : t("detail.analysis")}</h2></div><button onClick={reanalyze} disabled={actionLoading} className="secondary-button disabled:opacity-50">{request.intake_mode === "STRUCTURED" ? "Tính lại" : t("detail.reanalyze")}</button></div><p className="mt-2 text-sm">{request.ai_analysis.summary ?? t("detail.noSummary")}</p><div className="mt-3 grid gap-3 text-sm md:grid-cols-3"><Info label={t("detail.risks")} value={request.ai_analysis.detected_risks?.join(", ") || t("detail.none")} /><Info label={t("detail.missing")} value={request.ai_analysis.missing_information?.join(", ") || t("detail.none")} /><Info label={t("detail.confidence")} value={`${Math.round((request.ai_analysis.confidence ?? 0) * 100)}% · ${request.ai_metadata.provider ?? "mock"}${request.ai_fallback_used ? " · fallback" : ""}`} /></div><p className="mt-2 text-xs text-slate-500">Model: {request.ai_metadata.model_id ?? "-"} · Latency: {request.ai_metadata.latency_ms ?? "-"} ms {request.ai_metadata.error_code ? `· ${request.ai_metadata.error_code}` : ""}</p>{isDemo && <div className="mt-3"><button className="text-sm font-semibold text-sky-700" onClick={() => setShowTechnical(!showTechnical)}>{showTechnical ? "−" : "+"} {t("detail.raw")}</button>{showTechnical && <pre className="mt-2 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify({ analysis: request.ai_analysis, metadata: request.ai_metadata }, null, 2)}</pre>}</div>}</div>
        <div><h2 className="mb-2 font-bold">{t("detail.timeline")}</h2><ol className="space-y-2 border-l border-slate-200 pl-4 text-sm">{timeline.map((event) => <li key={event.id}><div className="font-semibold">{event.new_status} <span className="font-normal text-slate-500">· {event.changed_by}</span></div><div className="text-slate-500">{new Date(event.created_at).toLocaleString(locale)}{event.note ? ` · ${event.note}` : ""}</div></li>)}{!timeline.length && <li className="text-slate-500">{t("detail.noHistory")}</li>}</ol></div>
      </section>
      <aside className="space-y-4">
        <RequestMap requests={[request]} stations={stations} teams={teams} showNearestTeams />
        <div className="apple-utility-card"><h2 className="mb-3 text-[21px] font-semibold tracking-[-0.28px]">{t("detail.recommendations")}</h2><div className="space-y-3">{recommendations.map((item) => <div key={item.team_id} className="border-t border-slate-200 py-3 text-sm"><div className="font-semibold">{item.team_name} · {item.recommendation_score}/100</div><p>{item.estimated_distance_km === undefined ? t("detail.noDistance") : `${item.estimated_distance_km} ${t("detail.straightDistance")}`} · {item.vehicle_type ?? t("detail.noVehicle")}</p><p className="mt-1 text-slate-600">{item.reasons.join(" · ")}</p>{item.warnings.map((warning) => <p key={warning} className="mt-1 text-amber-700">⚠ {warning}</p>)}<button onClick={() => setTeamId(String(item.team_id))} className="secondary-button mt-2">{t("detail.chooseTeam")}</button></div>)}{!recommendations.length && <p className="text-sm text-slate-500">{t("detail.noTeam")}</p>}</div></div>
        <div className="apple-utility-card">
          <h2 className="mb-3 text-[21px] font-semibold tracking-[-0.28px]">{t("detail.assignment")}</h2>
          <p className="mb-3 text-sm text-slate-600">{t("detail.source")}: <strong>{request.source}</strong>{request.external_reference ? ` · ${request.external_reference}` : ""}{request.is_simulated ? " · simulator" : ""}</p>
          {request.assigned_team && <p className="mb-3 rounded bg-sky-50 p-3 text-sm text-sky-900">Đội đang phụ trách: <strong>{request.assigned_team.name}</strong></p>}
          <div className="space-y-3">
            {request.status === "PENDING_VERIFICATION" && <button onClick={verify} disabled={actionLoading} className="primary-button disabled:opacity-50">{t("detail.verify")}</button>}
            <select className="field" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              <option value="">{t("detail.chooseTeam")}</option>
              {teams.filter((team) => team.status === "AVAILABLE").map((team) => <option key={team.id} value={team.id}>{team.name} - {team.status}</option>)}
            </select>
            <textarea className="field min-h-20" placeholder={t("detail.dispatchNote")} value={note} onChange={(event) => setNote(event.target.value)} />
            <button onClick={assign} disabled={request.status !== "VERIFIED" || !teamId || actionLoading} className="primary-button disabled:cursor-not-allowed disabled:opacity-50">{t("detail.assign")}</button>
            {message && <p className="text-sm text-green-700">{message}</p>}
            {actionError && <p className="text-sm text-red-700">{actionError}</p>}
          </div>
        </div>
      </aside>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><div className="label">{label}</div><div className="font-medium">{value}</div></div>;
}

type FactsDraft = {
  message: string; address: string; latitude: string; longitude: string; number_of_people: string;
  number_of_children: string; number_of_elderly: string; number_of_injured: string; water_level: string;
  has_disabled_person: boolean; has_pregnant_person: boolean; is_trapped: boolean;
};

function VerifiedFactsForm({ request, loading, onCancel, onSave }: { request: RescueRequest; loading: boolean; onCancel: () => void; onSave: (values: Record<string, unknown>) => Promise<void> }) {
  const [draft, setDraft] = useState<FactsDraft>(() => ({
    message: request.message, address: request.address ?? "", latitude: valueOrEmpty(request.latitude), longitude: valueOrEmpty(request.longitude),
    number_of_people: String(request.number_of_people), number_of_children: String(request.number_of_children), number_of_elderly: String(request.number_of_elderly),
    number_of_injured: String(request.number_of_injured), water_level: valueOrEmpty(request.water_level), has_disabled_person: request.has_disabled_person,
    has_pregnant_person: request.has_pregnant_person, is_trapped: request.is_trapped,
  }));
  const textField = (field: keyof FactsDraft, label: string, type = "text") => <label className="space-y-1"><span className="label">{label}</span><input className="field" type={type} value={String(draft[field])} onChange={(event) => setDraft({ ...draft, [field]: event.target.value })} /></label>;
  const submit = () => onSave({
    message: draft.message, address: draft.address || null, latitude: optionalNumber(draft.latitude), longitude: optionalNumber(draft.longitude),
    number_of_people: requiredNumber(draft.number_of_people), number_of_children: requiredNumber(draft.number_of_children), number_of_elderly: requiredNumber(draft.number_of_elderly),
    number_of_injured: requiredNumber(draft.number_of_injured), water_level: optionalNumber(draft.water_level), has_disabled_person: draft.has_disabled_person,
    has_pregnant_person: draft.has_pregnant_person, is_trapped: draft.is_trapped,
  });
  return <div className="mt-4 space-y-4 rounded border border-[#e0e0e0] bg-[#fafafc] p-4">
    <label className="block space-y-1"><span className="label">Nội dung báo cáo</span><textarea className="field min-h-24" value={draft.message} onChange={(event) => setDraft({ ...draft, message: event.target.value })} /></label>
    <div className="grid gap-3 md:grid-cols-2">{textField("address", "Địa chỉ")}{textField("latitude", "Vĩ độ", "number")}{textField("longitude", "Kinh độ", "number")}{textField("number_of_people", "Tổng số người", "number")}{textField("number_of_children", "Trẻ em", "number")}{textField("number_of_elderly", "Người cao tuổi", "number")}{textField("number_of_injured", "Người bị thương", "number")}{textField("water_level", "Mực nước (m)", "number")}</div>
    <div className="flex flex-wrap gap-4 text-sm">{([['is_trapped', 'Đang mắc kẹt'], ['has_disabled_person', 'Có người khuyết tật'], ['has_pregnant_person', 'Có phụ nữ mang thai']] as const).map(([field, label]) => <label className="flex items-center gap-2" key={field}><input type="checkbox" checked={draft[field]} onChange={(event) => setDraft({ ...draft, [field]: event.target.checked })} />{label}</label>)}</div>
    <div className="flex gap-2"><button disabled={loading || !draft.message.trim()} className="primary-button disabled:opacity-50" onClick={() => void submit()}>Lưu và tính lại priority</button><button disabled={loading} className="secondary-button" onClick={onCancel}>Hủy</button></div>
  </div>;
}

function valueOrEmpty(value?: number) { return value == null ? "" : String(value); }
function optionalNumber(value: string) { return value.trim() === "" ? null : Number(value); }
function requiredNumber(value: string) { return Math.max(0, Number(value) || 0); }
