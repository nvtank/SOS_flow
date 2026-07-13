const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export type RescueTeam = {
  id: number;
  name: string;
  phone_number?: string;
  member_count: number;
  vehicle_type?: string;
  latitude?: number;
  longitude?: number;
  status: "AVAILABLE" | "BUSY" | "OFFLINE";
};

export type RescueRequest = {
  id: number;
  request_code: string;
  reporter_name?: string;
  phone_number?: string;
  message: string;
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
  ai_analysis: { summary?: string; detected_risks?: string[]; missing_information?: string[]; confidence?: number };
  priority_score: number;
  priority_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  priority_reasons: string[];
  status: string;
  assigned_team_id?: number;
  assigned_team?: RescueTeam;
  created_at: string;
  updated_at: string;
};

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

export type Statistics = {
  total_requests: number;
  critical_requests: number;
  pending_requests: number;
  active_rescues: number;
  completed_requests: number;
  available_teams: number;
};

export const api = {
  createRequest: (body: unknown) => request<RescueRequest>("/api/rescue-requests", { method: "POST", body: JSON.stringify(body) }),
  getRequests: (query = "") => request<RescueRequest[]>(`/api/admin/rescue-requests${query}`),
  getRequest: (id: string) => request<RescueRequest>(`/api/admin/rescue-requests/${id}`),
  getStats: () => request<Statistics>("/api/admin/statistics"),
  getTeams: () => request<RescueTeam[]>("/api/rescue-teams"),
  assign: (id: number, teamId: number, note?: string) => request<Mission>(`/api/admin/rescue-requests/${id}/assign`, { method: "POST", body: JSON.stringify({ team_id: teamId, note }) }),
  getTeamMissions: (teamId: string) => request<Mission[]>(`/api/rescue-teams/${teamId}/missions`),
  updateMission: (missionId: number, status: string, note?: string) => request<Mission>(`/api/missions/${missionId}/status`, { method: "PATCH", body: JSON.stringify({ status, note }) }),
};
