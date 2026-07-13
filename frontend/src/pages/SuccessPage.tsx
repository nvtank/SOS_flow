import { Link, useLocation } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Cpu } from "lucide-react";
import { RescueRequest } from "../api/client";
import { useI18n } from "../i18n";

export function SuccessPage() {
  const { locale, t } = useI18n();
  const { state } = useLocation();
  const request = state as RescueRequest | undefined;
  const bedrockSucceeded = request?.intake_mode === "NATURAL_LANGUAGE" && request.ai_metadata.bedrock_succeeded === true;
  const isStructured = request?.intake_mode === "STRUCTURED";
  return (
    <section className="apple-tile apple-tile--paper mx-auto max-w-3xl text-center">
      <h1 className="mb-4 text-[34px] font-semibold tracking-[-0.374px]">{t("success.title")}</h1>
      {request ? (
        <div className="mx-auto max-w-2xl space-y-4 text-left text-[#1d1d1f]">
          <p>{t("success.code")}: <strong>{request.request_code}</strong></p>
          <p>{t("success.status")}: <strong>{request.status}</strong></p>
          <p>{new Date(request.created_at).toLocaleString(locale)}</p>
          <div className={`rounded-[18px] border p-4 ${bedrockSucceeded || isStructured ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
            <div className="flex items-start gap-3">
              {bedrockSucceeded || isStructured ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" /> : <AlertTriangle className="mt-0.5 shrink-0 text-amber-700" />}
              <div>
                <strong>{isStructured ? t("success.ruleSuccess") : bedrockSucceeded ? t("success.bedrockSuccess") : t("success.bedrockFallback")}</strong>
                <p className="mt-1 text-sm">{request.ai_analysis.summary ?? "—"}</p>
                <p className="mt-2 font-mono text-xs text-slate-600">
                  provider={request.ai_metadata.provider ?? "—"} · model={request.ai_metadata.model_id ?? "—"} · latency={request.ai_metadata.latency_ms ?? 0}ms · fallback={String(request.ai_metadata.fallback_used ?? false)}
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-3 rounded-[18px] border border-slate-200 bg-white p-4 sm:grid-cols-2">
            <div><span className="text-xs text-slate-500">{t("success.priority")}</span><p className="font-semibold">{request.priority_level} · {request.priority_score}</p></div>
            <div><span className="text-xs text-slate-500">{t("detail.people")}</span><p className="font-semibold">{request.number_of_people} · {request.number_of_children} {t("form.children").toLowerCase()}</p></div>
            <div><span className="text-xs text-slate-500">{t("detail.water")}</span><p className="font-semibold">{request.water_level ?? "—"} m</p></div>
            <div><span className="text-xs text-slate-500">{t("detail.address")}</span><p className="font-semibold">{request.address ?? t("detail.unknown")}</p></div>
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-white p-4">
            <p className="mb-2 inline-flex items-center gap-2 font-semibold"><Cpu size={17} />{t("success.reasons")}</p>
            <ul className="space-y-1 text-sm text-slate-700">{request.priority_reasons.map((reason) => <li key={reason}>• {reason}</li>)}</ul>
          </div>
          <p className="pt-3 text-sm text-[#7a7a7a]">{t("success.keepPhone")}</p>
        </div>
      ) : (
        <p>{t("success.missing")}</p>
      )}
      <Link to="/report" className="primary-button mt-6 inline-flex">{t("success.another")}</Link>
    </section>
  );
}
