import L from "leaflet";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { RescueRequest } from "../api/client";
import { PriorityBadge, StatusBadge } from "./Badges";

const levelColor: Record<string, string> = {
  CRITICAL: "#b91c1c",
  HIGH: "#ea580c",
  MEDIUM: "#ca8a04",
  LOW: "#15803d",
};

export function RequestMap({ requests }: { requests: RescueRequest[] }) {
  const points = requests.filter((item) => item.latitude && item.longitude);
  const center: L.LatLngExpression = points.length ? [points[0].latitude!, points[0].longitude!] : [16.0471, 108.2068];

  return (
    <div className="h-[380px] overflow-hidden rounded border border-slate-200 bg-white">
      <MapContainer center={center} zoom={11} scrollWheelZoom>
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {points.map((request) => (
          <CircleMarker
            key={request.id}
            center={[request.latitude!, request.longitude!]}
            pathOptions={{ color: levelColor[request.priority_level], fillColor: levelColor[request.priority_level], fillOpacity: 0.75 }}
            radius={10}
          >
            <Popup>
              <div className="space-y-2 text-sm">
                <div className="font-bold">{request.request_code}</div>
                <p>{request.message}</p>
                <div>Số người: {request.number_of_people}</div>
                <div>Điểm: {request.priority_score}</div>
                <PriorityBadge level={request.priority_level} />
                <div><StatusBadge status={request.status} /></div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
