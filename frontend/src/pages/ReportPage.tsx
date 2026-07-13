import { FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BrainCircuit, ClipboardList, CloudOff, RefreshCw, Send, Trash2, Wifi, WifiOff } from "lucide-react";
import { api, ApiError } from "../api/client";
import { OfflineReport, makeOfflineReport, offlineQueue, syncQueuedReports } from "../offlineQueue";
import { useI18n } from "../i18n";

type IntakeMode = "STRUCTURED" | "NATURAL_LANGUAGE";

function payloadFromForm(form: FormData, intakeMode: IntakeMode): Record<string, unknown> {
  if (intakeMode === "NATURAL_LANGUAGE") {
    return { intake_mode: intakeMode, message: String(form.get("message") ?? "").trim() };
  }

  const body: Record<string, unknown> = { intake_mode: intakeMode };
  for (const field of ["reporter_name", "phone_number", "address"]) {
    const value = String(form.get(field) ?? "").trim();
    if (value) body[field] = value;
  }
  for (const field of ["number_of_adults", "number_of_children", "number_of_elderly", "number_of_injured", "water_level"]) {
    const value = String(form.get(field) ?? "").trim();
    if (value !== "") body[field] = Number(value);
  }
  for (const field of ["is_trapped", "has_disabled_person", "has_pregnant_person"]) {
    body[field] = form.has(field);
  }
  return body;
}

export function ReportPage() {
  const { locale, t } = useI18n();
  const navigate = useNavigate();
  const [intakeMode, setIntakeMode] = useState<IntakeMode>("NATURAL_LANGUAGE");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(navigator.onLine);
  const [reports, setReports] = useState<OfflineReport[]>([]);
  const [notice, setNotice] = useState("");
  const [lastSync, setLastSync] = useState<string>();

  const refreshQueue = useCallback(async () => setReports(await offlineQueue.list()), []);
  const sync = useCallback(async (force = false) => {
    if (!navigator.onLine) { setNotice(t("report.offlineNotice")); return; }
    const result = await syncQueuedReports(force);
    await refreshQueue();
    setLastSync(new Date().toLocaleTimeString(locale));
    if (result.synced) setNotice(t("report.synced").replace("{count}", String(result.synced)));
    if (result.failed) setError(t("report.syncFailed").replace("{count}", String(result.failed)));
  }, [locale, refreshQueue, t]);

  useEffect(() => {
    void refreshQueue();
    const onOnline = () => { setOnline(true); void sync(); };
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline); window.addEventListener("offline", onOffline);
    if (navigator.onLine) void sync();
    return () => { window.removeEventListener("online", onOnline); window.removeEventListener("offline", onOffline); };
  }, [refreshQueue, sync]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError(""); setNotice("");
    const formElement = event.currentTarget;
    const body = payloadFromForm(new FormData(formElement), intakeMode);
    // Reuse this key if the server accepts the report but the response is lost.
    // The backend then returns the original record instead of creating another.
    const clientSubmissionId = crypto.randomUUID();
    try {
      if (!navigator.onLine) {
        const local = makeOfflineReport(body, clientSubmissionId); await offlineQueue.put(local); await refreshQueue();
        formElement.reset();
        setNotice(t("report.savedLocal").replace("{id}", local.local_id));
        return;
      }
      const created = await api.createRequest({ ...body, client_submission_id: clientSubmissionId, source: "WEB" });
      navigate("/report/success", { state: created });
    } catch (err) {
      const detail = err instanceof Error ? err.message : t("report.sendFailed");
      // A 4xx means the user must correct the form; retrying the same invalid
      // payload forever would mislead them. Network and 5xx failures are safe
      // to queue with the original idempotency key.
      if (err instanceof ApiError && err.status < 500) { setError(detail); return; }
      const local = makeOfflineReport(body, clientSubmissionId); await offlineQueue.put(local); await refreshQueue();
      setError(`${detail}. ${t("report.queuedAfterFailure").replace("{id}", local.local_id)}`);
    } finally { setLoading(false); }
  }

  return <section className="report-page mx-auto max-w-5xl space-y-0">
    <div className="apple-hero"><div className="flex flex-wrap items-center justify-center gap-3"><h1>{t("report.title")}</h1><div className="inline-flex items-center gap-2 rounded-full border border-white/30 px-3 py-2 text-sm text-white">{online ? <Wifi size={16} /> : <WifiOff size={16} />}{online ? t("form.online") : t("form.offline")}</div></div><p>{t("report.dualSubtitle")}</p></div>
    {!online && <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><CloudOff className="mr-2 inline" size={16} />{t("report.offlineNotice")}</div>}

    <div className="report-mode-grid grid gap-3 bg-[#f5f5f7] p-5 md:grid-cols-2">
      <button type="button" onClick={() => setIntakeMode("NATURAL_LANGUAGE")} className={`rounded-[18px] border p-5 text-left transition ${intakeMode === "NATURAL_LANGUAGE" ? "border-[#0066cc] bg-white ring-2 ring-[#0066cc]/20" : "border-[#e0e0e0] bg-white/70"}`}>
        <BrainCircuit className="mb-3 text-[#0066cc]" size={28} /><strong className="block text-lg">{t("report.naturalTitle")}</strong><span className="mt-1 block text-sm text-slate-600">{t("report.naturalBody")}</span><span className="mt-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">Amazon Bedrock</span>
      </button>
      <button type="button" onClick={() => setIntakeMode("STRUCTURED")} className={`rounded-[18px] border p-5 text-left transition ${intakeMode === "STRUCTURED" ? "border-[#0066cc] bg-white ring-2 ring-[#0066cc]/20" : "border-[#e0e0e0] bg-white/70"}`}>
        <ClipboardList className="mb-3 text-[#0066cc]" size={28} /><strong className="block text-lg">{t("report.structuredTitle")}</strong><span className="mt-1 block text-sm text-slate-600">{t("report.structuredBody")}</span><span className="mt-3 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">Priority Engine · No AI</span>
      </button>
    </div>

    <form onSubmit={submit} className="apple-tile apple-tile--paper grid gap-5">
      {intakeMode === "NATURAL_LANGUAGE" ? <>
        <label><span className="label">{t("form.message")}</span><textarea required minLength={5} name="message" className="field min-h-40" placeholder={t("report.naturalExample")} /></label>
        <p className="rounded border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-950">{t("report.aiHint")}</p>
      </> : <>
        <div className="grid gap-4 md:grid-cols-2">
          <label><span className="label">{t("form.name")} *</span><input required name="reporter_name" className="field" placeholder="Nguyễn Văn A" /></label>
          <label><span className="label">{t("form.phone")}</span><input name="phone_number" className="field" inputMode="tel" /></label>
          <label><span className="label">{t("report.adults")} *</span><input required name="number_of_adults" className="field" type="number" min="0" defaultValue="1" /></label>
          <label><span className="label">{t("form.children")} *</span><input required name="number_of_children" className="field" type="number" min="0" defaultValue="0" /></label>
          <label><span className="label">{t("form.elderly")}</span><input name="number_of_elderly" className="field" type="number" min="0" defaultValue="0" /></label>
          <label><span className="label">{t("form.injured")}</span><input name="number_of_injured" className="field" type="number" min="0" defaultValue="0" /></label>
          <label><span className="label">{t("form.water")} *</span><input required name="water_level" className="field" type="number" min="0" step="0.1" placeholder="1.5" /></label>
          <label><span className="label">{t("form.address")}</span><input name="address" className="field" placeholder="Trà Linh, Đà Nẵng" /></label>
        </div>
        <div className="flex flex-wrap gap-5 text-sm">
          <label className="inline-flex items-center gap-2"><input name="is_trapped" type="checkbox" />{t("form.trapped")}</label>
          <label className="inline-flex items-center gap-2"><input name="has_disabled_person" type="checkbox" />{t("form.disabled")}</label>
          <label className="inline-flex items-center gap-2"><input name="has_pregnant_person" type="checkbox" />{t("form.pregnant")}</label>
        </div>
        <p className="rounded border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">{t("report.ruleHint")}</p>
      </>}
      {error && <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
      <button disabled={loading} className="primary-button inline-flex w-fit items-center gap-2 disabled:opacity-60"><Send size={18} /> {loading ? t("form.sending") : online ? t("form.send") : t("form.saveOffline")}</button>
    </form>
    <section className="apple-utility-card mt-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-[21px] font-semibold tracking-[-0.28px]">{t("form.localReports")} ({reports.length})</h2><p className="text-xs text-slate-500">{lastSync ?? "—"}</p></div><button onClick={() => void sync(true)} disabled={!online || !reports.length} className="secondary-button disabled:opacity-50"><RefreshCw size={15} /> {t("form.syncNow")}</button></div><div className="mt-3 space-y-2">{reports.map((report) => <div key={report.local_id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 py-3 text-sm"><div><strong>{report.local_id}</strong> · {report.sync_status} · {report.retry_count}<p className="text-slate-600">{String(report.form_data.message ?? report.form_data.reporter_name ?? "")}</p>{report.last_error && <p className="text-red-700">{report.last_error}</p>}</div><button onClick={() => void offlineQueue.remove(report.local_id).then(refreshQueue)} className="inline-flex items-center gap-1 text-red-700"><Trash2 size={15} /> Remove</button></div>)}{!reports.length && <p className="text-sm text-slate-500">{t("form.noQueue")}</p>}</div></section>
  </section>;
}
