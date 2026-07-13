import { useEffect, useMemo } from "react";
import L from "leaflet";
import { Circle, CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { RescueRequest, RescueStation, RescueTeam, SilentZone } from "../api/client";
import { DuplicateBadge, PriorityBadge, SourceBadge, StatusBadge } from "./Badges";
import { useI18n } from "../i18n";

export type MapArea = "ALL" | "TRA_LINH" | "DA_NANG";
type Located = { latitude: number; longitude: number };

const levelColor: Record<string, string> = { CRITICAL: "#b91c1c", HIGH: "#ea580c", MEDIUM: "#ca8a04", LOW: "#15803d" };
const AREA_LABELS: Record<MapArea, string> = { ALL: "Trà Linh + Đà Nẵng", TRA_LINH: "Trà Linh", DA_NANG: "Đà Nẵng" };

function isInArea(latitude: number, longitude: number, area: MapArea) {
  if (area === "ALL") return true;
  if (area === "TRA_LINH") return latitude >= 22.40 && latitude <= 22.65 && longitude >= 104.25 && longitude <= 104.60;
  return latitude >= 15.85 && latitude <= 16.25 && longitude >= 107.90 && longitude <= 108.35;
}

function FitCurrentPoints({ points }: { points: Array<{ latitude: number; longitude: number }> }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView([points[0].latitude, points[0].longitude], 13);
    if (points.length > 1) map.fitBounds(L.latLngBounds(points.map((item) => [item.latitude, item.longitude])), { padding: [32, 32], maxZoom: 13 });
  }, [map, points]);
  return null;
}

function distanceKm(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }) {
  const radians = (value: number) => value * Math.PI / 180;
  const [lat1, lon1, lat2, lon2] = [a.latitude, a.longitude, b.latitude, b.longitude].map(radians);
  const value = Math.sin((lat2 - lat1) / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2;
  return Math.round(6371 * 2 * Math.asin(Math.sqrt(value)) * 10) / 10;
}

function teamPoint(team: RescueTeam, stations: RescueStation[]) {
  if (team.current_latitude != null && team.current_longitude != null) return { latitude: team.current_latitude, longitude: team.current_longitude };
  if (team.station) return team.station;
  const station = stations.find((item) => item.id === team.station_id);
  if (station) return station;
  if (team.latitude != null && team.longitude != null) return { latitude: team.latitude, longitude: team.longitude };
  return undefined;
}

export function RequestMap({
  requests,
  zones = [],
  stations = [],
  teams = [],
  area = "ALL",
  showNearestTeams = false,
  showAssignedConnections = false,
  className = "h-[440px]",
}: {
  requests: RescueRequest[];
  zones?: SilentZone[];
  stations?: RescueStation[];
  teams?: RescueTeam[];
  area?: MapArea;
  showNearestTeams?: boolean;
  showAssignedConnections?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const points = useMemo(() => requests.filter((item): item is RescueRequest & Located => item.latitude != null && item.longitude != null && isInArea(item.latitude, item.longitude, area)), [requests, area]);
  const visibleStations = useMemo(() => stations.filter((station) => area === "ALL" || station.area_code === area), [stations, area]);
  const visibleZones = useMemo(() => zones.filter((zone) => isInArea(zone.latitude, zone.longitude, area)), [zones, area]);
  const boundsPoints = useMemo<Located[]>(() => [...points, ...visibleStations].map(({ latitude, longitude }) => ({ latitude, longitude })), [points, visibleStations]);
  const center: L.LatLngExpression = boundsPoints.length ? [boundsPoints[0].latitude, boundsPoints[0].longitude] : area === "TRA_LINH" ? [22.50, 104.41] : [16.06, 108.20];
  const nearestLines = useMemo(() => {
    if (!showNearestTeams || points.length !== 1) return [];
    const request = points[0];
    return teams.filter((team) => team.status === "AVAILABLE").map((team) => ({ team, point: teamPoint(team, stations) })).filter((item): item is { team: RescueTeam; point: { latitude: number; longitude: number } } => Boolean(item.point)).sort((left, right) => distanceKm(request, left.point) - distanceKm(request, right.point)).slice(0, 3).map((item) => ({ ...item, distance: distanceKm(request, item.point) }));
  }, [points, showNearestTeams, stations, teams]);
  const assignedLines = useMemo(() => points.map((request) => {
    const assigned = request.assigned_team ?? teams.find((team) => team.id === request.assigned_team_id);
    const point = assigned ? teamPoint(assigned, stations) : undefined;
    return assigned && point ? { request, team: assigned, point, distance: distanceKm(request, point) } : undefined;
  }).filter((item): item is { request: RescueRequest & Located; team: RescueTeam; point: Located; distance: number } => Boolean(item)), [points, stations, teams]);

  return <div className={`${className} rescue-map overflow-hidden rounded border border-slate-200 bg-white`}>
    <MapContainer center={center} zoom={area === "TRA_LINH" ? 12 : 11} scrollWheelZoom>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitCurrentPoints points={boundsPoints} />
      {visibleZones.map((zone) => <Circle key={`zone-${zone.id}`} center={[zone.latitude, zone.longitude]} radius={zone.radius_meters} pathOptions={{ color: zone.reason ? "#b45309" : "#64748b", fillColor: "#fbbf24", fillOpacity: zone.reason ? 0.16 : 0.05, dashArray: "6 6" }}><Popup><div className="space-y-1 text-sm"><strong>{t("dashboard.silentZones")}: {zone.name}</strong><p>{zone.reason ?? "—"}</p><p>{zone.silence_minutes === undefined ? "—" : `${Math.round(zone.silence_minutes)} min`}</p><p>{t("dashboard.status")}: {zone.verification_status}</p></div></Popup></Circle>)}
      {visibleStations.map((station) => {
        const stationTeams = teams.filter((team) => team.station_id === station.id);
        return <CircleMarker key={`station-${station.id}`} center={[station.latitude, station.longitude]} radius={11} pathOptions={{ color: "#083b7a", fillColor: "#0b63ce", fillOpacity: 1, weight: 3 }}>
          <Tooltip direction="top" offset={[0, -10]}>{station.name}</Tooltip>
          <Popup><div className="station-popup"><span className="station-popup__eyebrow">RESCUE STATION · {AREA_LABELS[station.area_code as MapArea] ?? station.area_code}</span><strong>{station.name}</strong><p>{station.address ?? "—"}</p><p className="station-popup__coords">{station.latitude.toFixed(4)}, {station.longitude.toFixed(4)}</p><div className="station-popup__teams">{stationTeams.length ? stationTeams.map((team) => <div key={team.id}><span>{team.name}</span><b>{team.status}</b></div>) : <span>Chưa gán đội</span>}</div><small>{station.is_simulated ? "Demo reference point" : "Fixed operational base"}</small></div></Popup>
        </CircleMarker>;
      })}
      {nearestLines.map(({ team, point, distance }) => <Polyline key={`nearest-${team.id}`} positions={[[points[0].latitude!, points[0].longitude!], [point.latitude, point.longitude]]} pathOptions={{ color: "#0b63ce", weight: 2, opacity: .65, dashArray: "6 7" }}><Tooltip sticky>{team.name} · {distance} km</Tooltip></Polyline>)}
      {showAssignedConnections && assignedLines.map(({ request, team, point, distance }) => <Polyline key={`assigned-${request.id}-${team.id}`} positions={[[request.latitude, request.longitude], [point.latitude, point.longitude]]} pathOptions={{ color: "#0b63ce", weight: 2, opacity: .72, dashArray: "4 6" }}><Tooltip sticky>{team.name} · {distance} km</Tooltip></Polyline>)}
      {points.map((request) => {
        const completed = ["COMPLETED", "FAILED"].includes(request.status);
        return <CircleMarker key={request.id} center={[request.latitude!, request.longitude!]} pathOptions={{ color: levelColor[request.priority_level], fillColor: levelColor[request.priority_level], fillOpacity: completed ? .25 : .78, opacity: completed ? .4 : 1 }} radius={request.priority_level === "CRITICAL" ? 12 : 9} eventHandlers={{ click: () => navigate(`/admin/requests/${request.id}`) }}>
          <Popup><div className="space-y-2 text-sm"><button className="font-bold text-sky-700" onClick={() => navigate(`/admin/requests/${request.id}`)}>{request.request_code}</button><p>{request.ai_analysis.summary ?? request.message}</p><div>{t("form.people")}: {request.number_of_people} · {t("dashboard.team")}: {request.assigned_team?.name ?? "—"}</div><div className="flex flex-wrap gap-1"><PriorityBadge level={request.priority_level} /><SourceBadge source={request.source} /><DuplicateBadge state={request.duplicate_state} /></div><StatusBadge status={request.status} /></div></Popup>
        </CircleMarker>;
      })}
    </MapContainer>
  </div>;
}
