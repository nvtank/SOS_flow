import { AlertTriangle, CheckCircle2, ClipboardCheck, Radio, Route, X } from "lucide-react";
import { useEffect } from "react";
import { useI18n } from "../i18n";

const steps = [
  { key: "step1", icon: Radio },
  { key: "step2", icon: ClipboardCheck },
  { key: "step3", icon: Route },
  { key: "step4", icon: AlertTriangle },
  { key: "step5", icon: CheckCircle2 },
];

export function UsageGuide({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open]);
  if (!open) return null;
  return <div className="guide-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="guide-panel" role="dialog" aria-modal="true" aria-labelledby="usage-guide-title">
      <header className="guide-panel__header">
        <div><span className="eyebrow">SOSFLOW PLAYBOOK</span><h2 id="usage-guide-title">{t("guide.title")}</h2><p>{t("guide.subtitle")}</p></div>
        <button className="icon-button" onClick={onClose} aria-label={t("common.close")}><X size={20} /></button>
      </header>
      <div className="guide-steps">
        {steps.map(({ key, icon: Icon }, index) => <article className="guide-step" key={key}>
          <div className="guide-step__icon"><Icon size={19} /></div>
          <div><h3>{t(`guide.${key}.title`)}</h3><p>{t(`guide.${key}.body`)}</p></div>
          {index < steps.length - 1 && <span className="guide-step__line" />}
        </article>)}
      </div>
      <div className="guide-tip"><AlertTriangle size={18} /><span>{t("guide.tip")}</span></div>
      <button className="primary-button w-full" onClick={onClose}>{t("common.close")}</button>
    </section>
  </div>;
}
