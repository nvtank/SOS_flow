const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); this.name = "ApiError"; }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const message = typeof detail.detail === "string" ? detail.detail : `Request failed: ${response.status}`;
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export type RescueTeam = {
  id: number;
  name: string;
  phone_number?: string;
  member_count: number;
  vehicle_type?: string;
  capabilities: string[];
  equipment: string[];
  max_people_capacity?: number;
  station_id?: number;
  station?: RescueStation;
  latitude?: number;
  longitude?: number;
  current_latitude?: number;
  current_longitude?: number;
  last_location_update?: string;
  status: "AVAILABLE" | "BUSY" | "OFFLINE";
  active_mission_count: number;
};

export type RescueStation = {
  id: number;
  code: string;
  name: string;
  area_code: "TRA_LINH" | "DA_NANG" | string;
  address?: string;
  latitude: number;
  longitude: number;
  is_simulated: boolean;
  is_active: boolean;
};

export type RescueRequest = {
  id: number;
  request_code: string;
  reporter_name?: string;
  phone_number?: string;
  message: string;
  intake_mode: "STRUCTURED" | "NATURAL_LANGUAGE";
  address?: string;
  latitude?: number;
  longitude?: number;
  number_of_people: number;
  number_of_children: number;
  number_of_elderly: number;
  number_of_injured: number;
  has_disabled_person: boolean;
  has_pregnant_person: boolean;
  is_trapped: boolean;
  water_level?: number;
  source: string;
  external_reference?: string;
  client_submission_id?: string;
  received_at: string;
  synced_at: string;
  is_simulated: boolean;
  raw_payload?: Record<string, unknown>;
  ai_analysis: { summary?: string; detected_risks?: string[]; missing_information?: string[]; confidence?: number };
  ai_metadata: { provider?: string; requested_provider?: string; model_id?: string; latency_ms?: number; analyzed_at?: string; ai_invoked?: boolean; bedrock_succeeded?: boolean; fallback_used?: boolean; error_code?: string; intake_mode?: string; auto_applied_fields?: string[] };
  ai_fallback_used: boolean;
  priority_score: number;
  priority_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  priority_reasons: string[];
  status: string;
  assigned_team_id?: number;
  canonical_request_id?: number;
  duplicate_state: "NOT_DUPLICATE" | "POSSIBLE_DUPLICATE" | "CONFIRMED_DUPLICATE";
  assigned_team?: RescueTeam;
  created_at: string;
  updated_at: string;
};

export type DuplicateCandidate = {
  id: number;
  request_id: number;
  candidate_request_id: number;
  duplicate_score: number;
  reasons: string[];
  confidence_level: string;
  status: "NOT_DUPLICATE" | "POSSIBLE_DUPLICATE" | "CONFIRMED_DUPLICATE";
  decision_note?: string;
  candidate_request: { id: number; request_code: string; message: string; address?: string; source: string; duplicate_state: string };
};

export type StatusHistory = { id: number; old_status?: string; new_status: string; changed_by: string; note?: string; created_at: string };
export type TeamRecommendation = { team_id: number; team_name: string; recommendation_score: number; estimated_distance_km?: number; vehicle_type?: string; capabilities: string[]; reasons: string[]; warnings: string[] };

export type Mission = {
  id: number;
  request_id: number;
  team_id: number;
  status: string;
  notes?: string;
  assigned_at: string;
  accepted_at?: string;
  arrived_at?: string;
  completed_at?: string;
  request: RescueRequest;
  team: RescueTeam;
};

export type MissionEvent = { id: number; mission_id: number; event_type: string; actor: string; note?: string; latitude?: number; longitude?: number; created_at: string };
export type DuplicateSummary = { request_id: number; canonical_request_id?: number; duplicate_state: RescueRequest["duplicate_state"]; merged_report_count: number };

export type Statistics = {
  total_requests: number;
  critical_requests: number;
  high_requests: number;
  pending_verification: number;
  pending_requests: number;
  verified: number;
  assigned: number;
  active_rescues: number;
  completed_requests: number;
  completed: number;
  failed: number;
  blocked_rescues: number;
  reinforcement_rescues: number;
  available_teams: number;
  busy_teams: number;
  offline_teams: number;
  requests_by_priority: MetricBucket[];
  requests_by_status: MetricBucket[];
  requests_by_source: MetricBucket[];
  requests_over_time: TimeMetricBucket[];
  requests_over_time_minutes: TimeMetricBucket[];
  average_waiting_minutes: number;
  average_time_to_assign?: number;
  average_time_to_arrive?: number;
  average_completion_time?: number;
  missing_location_count: number;
  duplicate_candidates_count: number;
  unassigned_critical_count: number;
  silent_zone_alerts_count: number;
  action_alerts: DashboardAlert[];
};

export type SilentZone = { id: number; name: string; latitude: number; longitude: number; radius_meters: number; hazard_active: boolean; last_report_at?: string; silence_threshold_minutes: number; verification_status: string; silence_minutes?: number; reason?: string; };
export type DemoScenarioState = { scenario: string; next_event: number; total_events: number; paused: boolean; speed: number; complete: boolean; event?: string; request_ids?: number[]; injected?: { event: string; request_ids: number[] }[] };

export type MetricBucket = { label: string; value: number };
export type TimeMetricBucket = { bucket: string; value: number };
export type DashboardAlert = { key: string; label: string; count: number; severity: string };

export type PaginatedRescueRequests = {
  items: RescueRequest[];
  page: number;
  page_size: number;
  total: number;
};

export const api = {
  createRequest: (body: unknown) => request<RescueRequest>("/api/rescue-requests", { method: "POST", body: JSON.stringify(body) }),
  getRequests: (query = "") => request<PaginatedRescueRequests>(`/api/admin/rescue-requests${query}`),
  getRequest: (id: string) => request<RescueRequest>(`/api/admin/rescue-requests/${id}`),
  updateRequest: (id: number, body: unknown) => request<RescueRequest>(`/api/admin/rescue-requests/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  reanalyze: (id: number) => request<RescueRequest>(`/api/admin/rescue-requests/${id}/reanalyze`, { method: "POST" }),
  getTeamRecommendations: (id: number) => request<TeamRecommendation[]>(`/api/admin/rescue-requests/${id}/team-recommendations`),
  getDuplicates: (id: number) => request<DuplicateCandidate[]>(`/api/admin/rescue-requests/${id}/duplicates`),
  getDuplicateSummary: (id: number) => request<DuplicateSummary>(`/api/admin/rescue-requests/${id}/duplicate-summary`),
  getTimeline: (id: number) => request<StatusHistory[]>(`/api/admin/rescue-requests/${id}/timeline`),
  confirmDuplicate: (id: number, candidateId: number, note?: string) => request<DuplicateCandidate>(`/api/admin/rescue-requests/${id}/duplicates/${candidateId}/confirm`, { method: "POST", body: JSON.stringify({ note }) }),
  rejectDuplicate: (id: number, candidateId: number, note?: string) => request<DuplicateCandidate>(`/api/admin/rescue-requests/${id}/duplicates/${candidateId}/reject`, { method: "POST", body: JSON.stringify({ note }) }),
  mergeDuplicate: (id: number, candidateId: number, canonicalRequestId: number, note?: string) => request<RescueRequest>(`/api/admin/rescue-requests/${id}/merge`, { method: "POST", body: JSON.stringify({ candidate_id: candidateId, canonical_request_id: canonicalRequestId, note }) }),
  getStats: () => request<Statistics>("/api/admin/statistics"),
  getSilentZones: (alertsOnly = false) => request<SilentZone[]>(`/api/admin/silent-zones${alertsOnly ? "?alerts_only=true" : ""}`),
  updateSilentZone: (id: number, status: string, note?: string) => request<SilentZone>(`/api/admin/silent-zones/${id}/verification`, { method: "PATCH", body: JSON.stringify({ status, note }) }),
  getTeams: () => request<RescueTeam[]>("/api/rescue-teams"),
  getRescueStations: (areaCode?: string) => request<RescueStation[]>(`/api/rescue-stations${areaCode ? `?area_code=${encodeURIComponent(areaCode)}` : ""}`),
  assign: (id: number, teamId: number, note?: string) => request<Mission>(`/api/admin/rescue-requests/${id}/assign`, { method: "POST", body: JSON.stringify({ team_id: teamId, note }) }),
  getTeamMissions: (teamId: string) => request<Mission[]>(`/api/rescue-teams/${teamId}/missions`),
  getMissionEvents: (missionId: number) => request<MissionEvent[]>(`/api/missions/${missionId}/events`),
  updateMission: (missionId: number, status: string, note?: string) => request<Mission>(`/api/missions/${missionId}/status`, { method: "PATCH", body: JSON.stringify({ status, note }) }),
  demoStatus: (token: string) => request<DemoScenarioState>("/api/demo/scenario", { headers: { "X-Demo-Token": token } }),
  demoStart: (token: string, speed: number) => request<DemoScenarioState>("/api/demo/scenario/start", { method: "POST", headers: { "X-Demo-Token": token }, body: JSON.stringify({ speed }) }),
  demoPause: (token: string, paused: boolean) => request<DemoScenarioState>(`/api/demo/scenario/pause?paused=${paused}`, { method: "POST", headers: { "X-Demo-Token": token } }),
  demoSpeed: (token: string, speed: number) => request<DemoScenarioState>("/api/demo/scenario/speed", { method: "POST", headers: { "X-Demo-Token": token }, body: JSON.stringify({ speed }) }),
  demoNext: (token: string) => request<DemoScenarioState>("/api/demo/scenario/next", { method: "POST", headers: { "X-Demo-Token": token } }),
  demoAll: (token: string) => request<DemoScenarioState>("/api/demo/scenario/all", { method: "POST", headers: { "X-Demo-Token": token } }),
  demoReset: (token: string) => request<DemoScenarioState>("/api/demo/scenario/reset", { method: "POST", headers: { "X-Demo-Token": token } }),
};
