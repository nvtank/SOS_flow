import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import "./styles/index.css";
import { Layout } from "./components/Layout";
import { ReportPage } from "./pages/ReportPage";
import { SuccessPage } from "./pages/SuccessPage";
import { I18nProvider } from "./i18n";

// Keep Reporter in the entry bundle for the offline shell; split heavier admin
// map/table screens so the emergency form loads quickly on a weak connection.
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const RequestDetailPage = lazy(() => import("./pages/RequestDetailPage").then((module) => ({ default: module.RequestDetailPage })));
const RequestsPage = lazy(() => import("./pages/RequestsPage").then((module) => ({ default: module.RequestsPage })));
const RescueMissionsPage = lazy(() => import("./pages/RescueMissionsPage").then((module) => ({ default: module.RescueMissionsPage })));
const TeamsPage = lazy(() => import("./pages/TeamsPage").then((module) => ({ default: module.TeamsPage })));

const screen = (node: React.ReactNode) => <Suspense fallback={<div className="apple-utility-card">Đang tải…</div>}>{node}</Suspense>;

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => void navigator.serviceWorker.register("/sw.js"));
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Navigate to="/admin/dashboard" replace /> },
      { path: "/report", element: <ReportPage /> },
      { path: "/report/success", element: <SuccessPage /> },
      { path: "/admin/dashboard", element: screen(<DashboardPage />) },
      { path: "/admin/requests", element: screen(<RequestsPage />) },
      { path: "/admin/requests/:id", element: screen(<RequestDetailPage />) },
      { path: "/admin/teams", element: screen(<TeamsPage />) },
      { path: "/rescue/:teamId/missions", element: screen(<RescueMissionsPage />) },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <RouterProvider router={router} />
    </I18nProvider>
  </React.StrictMode>
);
