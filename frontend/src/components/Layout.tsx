import { AlertTriangle, BarChart3, BookOpen, ClipboardList, Globe2, Radio, Users } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { Language, useI18n } from "../i18n";
import { UsageGuide } from "./UsageGuide";

const links = [
  { to: "/admin/dashboard", key: "nav.dashboard", icon: BarChart3 },
  { to: "/admin/requests", key: "nav.requests", icon: ClipboardList },
  { to: "/admin/teams", key: "nav.teams", icon: Users },
  { to: "/report", key: "nav.report", icon: AlertTriangle },
];

export function Layout() {
  const { language, setLanguage, t } = useI18n();
  const [guideOpen, setGuideOpen] = useState(false);
  return <div className="app-shell">
    <header className="command-topbar">
      <Link to="/admin/dashboard" className="brand" aria-label="SOSFlow home">
        <span className="brand__mark"><Radio size={20} /></span>
        <span><strong>SOSFlow</strong><small>{t("layout.commandCenter")}</small></span>
      </Link>
      <div className="topbar-actions">
        <span className="system-live"><i />{t("layout.live")}</span>
        <button className="guide-button" onClick={() => setGuideOpen(true)}><BookOpen size={17} /><span>{t("layout.guide")}</span></button>
        <div className="language-switcher" aria-label={t("layout.language")}>
          <Globe2 size={15} />
          {(["vi", "en", "ko"] as Language[]).map((item) => <button key={item} aria-pressed={language === item} className={language === item ? "active" : ""} onClick={() => setLanguage(item)}>{item === "vi" ? "VI" : item === "en" ? "EN" : "한"}</button>)}
        </div>
      </div>
    </header>
    <div className="command-layout">
      <aside className="command-sidebar">
        <nav aria-label="Primary">
          {links.map(({ to, key, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}><Icon size={19} /><span>{t(key)}</span></NavLink>)}
        </nav>
        <button className="sidebar-guide" onClick={() => setGuideOpen(true)}><BookOpen size={18} /><span>{t("layout.guide")}</span></button>
      </aside>
      <main className="command-main"><Outlet /></main>
    </div>
    <UsageGuide open={guideOpen} onClose={() => setGuideOpen(false)} />
  </div>;
}
