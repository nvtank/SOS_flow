import { AlertTriangle, ClipboardList, MapPinned, Users } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/report", label: "Reporter", icon: AlertTriangle },
  { to: "/admin/dashboard", label: "Dashboard", icon: MapPinned },
  { to: "/admin/requests", label: "Requests", icon: ClipboardList },
  { to: "/admin/teams", label: "Teams", icon: Users },
];

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/admin/dashboard" className="text-xl font-bold text-command">SOSFlow</Link>
          <nav className="flex flex-wrap gap-2">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `inline-flex items-center gap-2 rounded px-3 py-2 text-sm font-semibold ${isActive ? "bg-command text-white" : "text-slate-700 hover:bg-slate-100"}`}>
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">
        <Outlet />
      </main>
    </div>
  );
}
