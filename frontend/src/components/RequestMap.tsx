import { useEffect, useMemo } from "react";
import L from "leaflet";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { RescueRequest, SilentZone } from "../api/client";
import { DuplicateBadge, PriorityBadge, SourceBadge, StatusBadge } from "./Badges";
import { useI18n } from "../i18n";

const levelColor: Record<string, string> = {
  CRITICAL: "#b91c1c",
  HIGH: "#ea580c",
  MEDIUM: "#ca8a04",
  LOW: "#15803d",
};

function FitCurrentPoints({ points }: { points: RescueRequest[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView([points[0].latitude!, points[0].longitude!], 14);
    if (points.length > 1) map.fitBounds(L.latLngBounds(points.map((item) => [item.latitude!, item.longitude!])), { padding: [24, 24], maxZoom: 14 });
  }, [map, points]);
  return null;
}

export function RequestMap({ requests, zones = [], className = "h-[440px]" }: { requests: RescueRequest[]; zones?: SilentZone[]; className?: string }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const points = useMemo(() => requests.filter((item) => item.latitude !== undefined && item.latitude !== null && item.longitude !== undefined && item.longitude !== null), [requests]);
  const center: L.LatLngExpression = points.length ? [points[0].latitude!, points[0].longitude!] : [16.0471, 108.2068];

  return (
    <div className={`${className} overflow-hidden rounded border border-slate-200 bg-white`}>
      <MapContainer center={center} zoom={11} scrollWheelZoom>
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitCurrentPoints points={points} />
        {zones.map((zone) => <Circle key={`zone-${zone.id}`} center={[zone.latitude, zone.longitude]} radius={zone.radius_meters} pathOptions={{ color: zone.reason ? "#b45309" : "#64748b", fillColor: "#fbbf24", fillOpacity: zone.reason ? 0.16 : 0.05, dashArray: "6 6" }}><Popup><div className="space-y-1 text-sm"><strong>{t("dashboard.silentZones")}: {zone.name}</strong><p>{zone.reason ?? "—"}</p><p>{zone.silence_minutes === undefined ? "—" : `${Math.round(zone.silence_minutes)} min`}</p><p>{t("dashboard.status")}: {zone.verification_status}</p></div></Popup></Circle>)}
        {points.map((request) => {
          const completed = ["COMPLETED", "FAILED"].includes(request.status);
          return <CircleMarker
            key={request.id}
            center={[request.latitude!, request.longitude!]}
            pathOptions={{ color: levelColor[request.priority_level], fillColor: levelColor[request.priority_level], fillOpacity: completed ? 0.25 : 0.78, opacity: completed ? 0.4 : 1 }}
            radius={request.priority_level === "CRITICAL" ? 12 : 9}
            eventHandlers={{ click: () => navigate(`/admin/requests/${request.id}`) }}
          >
            <Popup>
              <div className="space-y-2 text-sm">
                <button className="font-bold text-sky-700" onClick={() => navigate(`/admin/requests/${request.id}`)}>{request.request_code}</button>
                <p>{request.ai_analysis.summary ?? request.message}</p>
                <div>{t("form.people")}: {request.number_of_people} · {t("dashboard.team")}: {request.assigned_team?.name ?? "—"}</div>
                <div className="flex flex-wrap gap-1"><PriorityBadge level={request.priority_level} /><SourceBadge source={request.source} /><DuplicateBadge state={request.duplicate_state} /></div>
                <StatusBadge status={request.status} />
              </div>
            </Popup>
          </CircleMarker>;
        })}
      </MapContainer>
    </div>
  );
}
