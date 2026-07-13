import { FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CloudOff, RefreshCw, Send, Trash2, Wifi, WifiOff } from "lucide-react";
import { api } from "../api/client";
import { OfflineReport, makeOfflineReport, offlineQueue, syncQueuedReports } from "../offlineQueue";
import { useI18n } from "../i18n";

export function ReportPage() {
  const { locale, t } = useI18n();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(navigator.onLine);
  const [reports, setReports] = useState<OfflineReport[]>([]);
  const [notice, setNotice] = useState("");
  const [lastSync, setLastSync] = useState<string>();

  const refreshQueue = useCallback(async () => setReports(await offlineQueue.list()), []);
  const sync = useCallback(async (force = false) => {
    if (!navigator.onLine) { setNotice("Thiết bị đang offline; báo cáo vẫn được lưu an toàn trên thiết bị."); return; }
    const result = await syncQueuedReports(force);
    await refreshQueue();
    setLastSync(new Date().toLocaleTimeString(locale));
    if (result.synced) setNotice(`Đã đồng bộ ${result.synced} báo cáo về trung tâm.`);
    if (result.failed) setError(`${result.failed} báo cáo chưa đồng bộ được; hệ thống sẽ thử lại với backoff.`);
  }, [locale, refreshQueue]);

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
    const form = new FormData(formElement);
    const body: Record<string, unknown> = Object.fromEntries(form.entries());
    const numeric = ["latitude", "longitude", "number_of_people", "number_of_children", "number_of_elderly", "number_of_injured", "water_level"];
    numeric.forEach((key) => { if (body[key] === "") delete body[key]; else if (body[key] !== undefined) body[key] = Number(body[key]); });
    body.has_disabled_person = form.has("has_disabled_person"); body.has_pregnant_person = form.has("has_pregnant_person"); body.is_trapped = form.has("is_trapped");
    try {
      if (!navigator.onLine) {
        const local = makeOfflineReport(body); await offlineQueue.put(local); await refreshQueue();
        formElement.reset();
        setNotice(`Báo cáo ${local.local_id} đang được lưu trên thiết bị và chưa gửi về trung tâm.`);
        return;
      }
      const clientSubmissionId = crypto.randomUUID();
      const created = await api.createRequest({ ...body, client_submission_id: clientSubmissionId, source: "WEB" });
      navigate("/report/success", { state: created });
    } catch (err) {
      // A network failure during an online submission is queued rather than discarded.
      const local = makeOfflineReport(body); await offlineQueue.put(local); await refreshQueue();
      setError(err instanceof Error ? `${err.message}. Đã lưu ${local.local_id} để đồng bộ lại.` : `Đã lưu ${local.local_id} để đồng bộ lại.`);
    } finally { setLoading(false); }
  }

  return <section className="mx-auto max-w-4xl space-y-0">
    <div className="apple-hero"><div className="flex flex-wrap items-center justify-center gap-3"><h1>{t("report.title")}</h1><div className="inline-flex items-center gap-2 rounded-full border border-white/30 px-3 py-2 text-sm text-white">{online ? <Wifi size={16} /> : <WifiOff size={16} />}{online ? t("form.online") : t("form.offline")}</div></div><p>{t("report.subtitle")}</p></div>
    {!online && <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><CloudOff className="mr-2 inline" size={16} />Báo cáo đang được lưu trên thiết bị và chưa gửi về trung tâm. Không đóng dữ liệu trình duyệt trước khi đồng bộ.</div>}
    <form onSubmit={submit} className="apple-tile apple-tile--paper grid gap-5">
      <div className="grid gap-4 md:grid-cols-2"><label><span className="label">{t("form.name")}</span><input name="reporter_name" className="field" /></label><label><span className="label">{t("form.phone")}</span><input name="phone_number" className="field" /></label></div>
      <label><span className="label">{t("form.message")}</span><textarea required name="message" className="field min-h-28" placeholder={t("form.messageHint")} /></label>
      <label><span className="label">{t("form.address")}</span><input name="address" className="field" /></label>
      <div className="grid gap-4 md:grid-cols-2"><label><span className="label">Latitude</span><input name="latitude" type="number" step="any" className="field" /></label><label><span className="label">Longitude</span><input name="longitude" type="number" step="any" className="field" /></label></div>
      <div className="grid gap-4 md:grid-cols-4"><label><span className="label">{t("form.people")}</span><input name="number_of_people" type="number" min="0" defaultValue="1" className="field" /></label><label><span className="label">{t("form.children")}</span><input name="number_of_children" type="number" min="0" defaultValue="0" className="field" /></label><label><span className="label">{t("form.elderly")}</span><input name="number_of_elderly" type="number" min="0" defaultValue="0" className="field" /></label><label><span className="label">{t("form.injured")}</span><input name="number_of_injured" type="number" min="0" defaultValue="0" className="field" /></label></div>
      <div className="grid gap-4 md:grid-cols-2"><label><span className="label">{t("form.water")}</span><input name="water_level" type="number" min="0" step="0.1" className="field" /></label><label><span className="label">{t("form.note")}</span><input name="note" className="field" /></label></div>
      <div className="flex flex-wrap gap-4 text-sm"><label className="inline-flex items-center gap-2"><input type="checkbox" name="is_trapped" /> {t("form.trapped")}</label><label className="inline-flex items-center gap-2"><input type="checkbox" name="has_disabled_person" /> {t("form.disabled")}</label><label className="inline-flex items-center gap-2"><input type="checkbox" name="has_pregnant_person" /> {t("form.pregnant")}</label></div>
      {error && <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
      <button disabled={loading} className="primary-button inline-flex w-fit items-center gap-2 disabled:opacity-60"><Send size={18} /> {loading ? t("form.sending") : online ? t("form.send") : t("form.saveOffline")}</button>
    </form>
    <section className="apple-utility-card mt-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-[21px] font-semibold tracking-[-0.28px]">{t("form.localReports")} ({reports.length})</h2><p className="text-xs text-slate-500">{lastSync ?? "—"}</p></div><button onClick={() => void sync(true)} disabled={!online || !reports.length} className="secondary-button disabled:opacity-50"><RefreshCw size={15} /> {t("form.syncNow")}</button></div><div className="mt-3 space-y-2">{reports.map((report) => <div key={report.local_id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 py-3 text-sm"><div><strong>{report.local_id}</strong> · {report.sync_status} · {report.retry_count}<p className="text-slate-600">{String(report.form_data.message ?? "")}</p>{report.last_error && <p className="text-red-700">{report.last_error}</p>}</div><button onClick={() => void offlineQueue.remove(report.local_id).then(refreshQueue)} className="inline-flex items-center gap-1 text-red-700"><Trash2 size={15} /> Remove</button></div>)}{!reports.length && <p className="text-sm text-slate-500">{t("form.noQueue")}</p>}</div></section>
  </section>;
}
