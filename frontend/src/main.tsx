import React from "react";
import ReactDOM from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";
import "./styles/index.css";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { ReportPage } from "./pages/ReportPage";
import { SuccessPage } from "./pages/SuccessPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { RequestsPage } from "./pages/RequestsPage";
import { RescueMissionsPage } from "./pages/RescueMissionsPage";
import { TeamsPage } from "./pages/TeamsPage";
import { I18nProvider } from "./i18n";

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
      { path: "/admin/dashboard", element: <DashboardPage /> },
      { path: "/admin/requests", element: <RequestsPage /> },
      { path: "/admin/requests/:id", element: <RequestDetailPage /> },
      { path: "/admin/teams", element: <TeamsPage /> },
      { path: "/rescue/:teamId/missions", element: <RescueMissionsPage /> },
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
