import { Link, useLocation } from "react-router-dom";
import { RescueRequest } from "../api/client";
import { useI18n } from "../i18n";

export function SuccessPage() {
  const { locale, t } = useI18n();
  const { state } = useLocation();
  const request = state as RescueRequest | undefined;
  return (
    <section className="apple-tile apple-tile--paper mx-auto max-w-2xl text-center">
      <h1 className="mb-4 text-[34px] font-semibold tracking-[-0.374px]">{t("success.title")}</h1>
      {request ? (
        <div className="mx-auto max-w-md space-y-2 text-left text-[#1d1d1f]">
          <p>{t("success.code")}: <strong>{request.request_code}</strong></p>
          <p>{t("success.status")}: <strong>{request.status}</strong></p>
          <p>{new Date(request.created_at).toLocaleString(locale)}</p>
          <p className="pt-3 text-sm text-[#7a7a7a]">{t("success.keepPhone")}</p>
        </div>
      ) : (
        <p>{t("success.missing")}</p>
      )}
      <Link to="/report" className="primary-button mt-6 inline-flex">{t("success.another")}</Link>
    </section>
  );
}
