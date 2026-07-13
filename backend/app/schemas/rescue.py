from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.core.time import as_utc
from app.models.entities import IntakeSource


class UTCResponseModel(BaseModel):
    """Serialize both legacy SQLite values and PostgreSQL values as UTC ISO-8601."""

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_datetimes_as_utc(self, value: Any):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            else:
                value = value.astimezone(UTC)
            return value.isoformat().replace("+00:00", "Z")
        return value


class RescueRequestCreate(BaseModel):
    reporter_name: str | None = None
    phone_number: str | None = None
    message: str = Field(..., min_length=5)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    number_of_people: int = Field(default=1, ge=0)
    number_of_children: int = Field(default=0, ge=0)
    number_of_elderly: int = Field(default=0, ge=0)
    number_of_injured: int = Field(default=0, ge=0)
    has_disabled_person: bool = False
    has_pregnant_person: bool = False
    is_trapped: bool = False
    water_level: float | None = Field(default=None, ge=0)
    source: IntakeSource = IntakeSource.WEB
    external_reference: str | None = Field(default=None, max_length=160)
    client_submission_id: str | None = Field(default=None, max_length=160)
    received_at: datetime | None = None
    is_simulated: bool = False
    raw_payload: dict[str, Any] | None = None
    note: str | None = None

    @field_validator("received_at")
    @classmethod
    def normalize_received_at(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else None


class RescueStationOut(UTCResponseModel):
    id: int
    code: str
    name: str
    area_code: str
    address: str | None
    latitude: float
    longitude: float
    is_simulated: bool
    is_active: bool

    model_config = {"from_attributes": True}


class RescueTeamOut(UTCResponseModel):
    id: int
    name: str
    phone_number: str | None
    member_count: int
    vehicle_type: str | None
    capabilities: list[str]
    equipment: list[str]
    max_people_capacity: int | None
    station_id: int | None
    station: RescueStationOut | None = None
    latitude: float | None
    longitude: float | None
    current_latitude: float | None
    current_longitude: float | None
    last_location_update: datetime | None
    active_mission_count: int
    status: str

    model_config = {"from_attributes": True}


class RescueRequestOut(UTCResponseModel):
    id: int
    request_code: str
    reporter_name: str | None
    phone_number: str | None
    message: str
    address: str | None
    latitude: float | None
    longitude: float | None
    number_of_people: int
    number_of_children: int
    number_of_elderly: int
    number_of_injured: int
    has_disabled_person: bool
    has_pregnant_person: bool
    is_trapped: bool
    water_level: float | None
    source: str
    external_reference: str | None
    client_submission_id: str | None
    received_at: datetime
    synced_at: datetime
    is_simulated: bool
    raw_payload: dict[str, Any] | None
    ai_analysis: dict[str, Any]
    ai_metadata: dict[str, Any]
    ai_fallback_used: bool
    priority_score: int
    priority_level: str
    priority_reasons: list[str]
    status: str
    assigned_team_id: int | None
    canonical_request_id: int | None
    duplicate_state: str
    assigned_team: RescueTeamOut | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequestStatusOut(UTCResponseModel):
    request_code: str
    status: str
    priority_level: str
    priority_score: int
    created_at: datetime
    updated_at: datetime


class RescueRequestUpdate(BaseModel):
    reporter_name: str | None = None
    phone_number: str | None = None
    message: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    number_of_people: int | None = Field(default=None, ge=0)
    number_of_children: int | None = Field(default=None, ge=0)
    number_of_elderly: int | None = Field(default=None, ge=0)
    number_of_injured: int | None = Field(default=None, ge=0)
    has_disabled_person: bool | None = None
    has_pregnant_person: bool | None = None
    is_trapped: bool | None = None
    water_level: float | None = Field(default=None, ge=0)
    status: str | None = None
    note: str | None = None


class AssignRequest(BaseModel):
    team_id: int
    note: str | None = None


class RescueTeamCreate(BaseModel):
    name: str
    phone_number: str | None = None
    member_count: int = Field(default=4, ge=1)
    vehicle_type: str | None = None
    capabilities: list[str] = Field(default_factory=list, max_length=30)
    equipment: list[str] = Field(default_factory=list, max_length=30)
    max_people_capacity: int | None = Field(default=None, ge=1)
    station_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    last_location_update: datetime | None = None
    status: str = "AVAILABLE"

    @field_validator("capabilities", "equipment")
    @classmethod
    def validate_team_metadata(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip().lower() for value in values if value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("capabilities and equipment cannot contain duplicates")
        return cleaned


class MissionOut(UTCResponseModel):
    id: int
    request_id: int
    team_id: int
    status: str
    notes: str | None
    assigned_at: datetime
    accepted_at: datetime | None
    arrived_at: datetime | None
    completed_at: datetime | None
    request: RescueRequestOut
    team: RescueTeamOut

    model_config = {"from_attributes": True}


class MissionStatusUpdate(BaseModel):
    status: str
    note: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class MissionEventOut(UTCResponseModel):
    id: int
    mission_id: int
    event_type: str
    actor: str
    note: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamRecommendationOut(UTCResponseModel):
    team_id: int
    team_name: str
    recommendation_score: int
    estimated_distance_km: float | None
    vehicle_type: str | None
    capabilities: list[str]
    reasons: list[str]
    warnings: list[str]


class StatusHistoryOut(UTCResponseModel):
    id: int
    request_id: int
    old_status: str | None
    new_status: str
    changed_by: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedRescueRequests(UTCResponseModel):
    items: list[RescueRequestOut]
    page: int
    page_size: int
    total: int


class MetricBucket(UTCResponseModel):
    label: str
    value: int


class TimeMetricBucket(UTCResponseModel):
    bucket: str
    value: int


class DashboardAlert(UTCResponseModel):
    key: str
    label: str
    count: int
    severity: str


class SilentZoneOut(UTCResponseModel):
    id: int
    name: str
    scenario_key: str | None
    latitude: float
    longitude: float
    radius_meters: int
    hazard_active: bool
    last_report_at: datetime | None
    silence_threshold_minutes: int
    verification_status: str
    silence_minutes: float | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SilentZoneStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class SilentZoneHistoryOut(UTCResponseModel):
    id: int
    zone_id: int
    old_status: str | None
    new_status: str
    actor: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DemoScenarioControl(BaseModel):
    speed: int = Field(default=1, ge=1, le=5)


class StatisticsOut(UTCResponseModel):
    total_requests: int
    critical_requests: int
    high_requests: int
    pending_verification: int
    pending_requests: int
    verified: int
    assigned: int
    active_rescues: int
    completed_requests: int
    completed: int
    failed: int
    blocked_rescues: int
    reinforcement_rescues: int
    available_teams: int
    busy_teams: int
    offline_teams: int
    requests_by_priority: list[MetricBucket]
    requests_by_status: list[MetricBucket]
    requests_by_source: list[MetricBucket]
    requests_over_time: list[TimeMetricBucket]
    requests_over_time_minutes: list[TimeMetricBucket]
    average_waiting_minutes: float
    average_time_to_assign: float | None
    average_time_to_arrive: float | None
    average_completion_time: float | None
    missing_location_count: int
    duplicate_candidates_count: int
    unassigned_critical_count: int
    silent_zone_alerts_count: int
    action_alerts: list[DashboardAlert]


class DuplicateRequestSummary(UTCResponseModel):
    id: int
    request_code: str
    message: str
    address: str | None
    source: str
    received_at: datetime
    duplicate_state: str
    canonical_request_id: int | None

    model_config = {"from_attributes": True}


class DuplicateCandidateOut(UTCResponseModel):
    id: int
    request_id: int
    candidate_request_id: int
    duplicate_score: float
    reasons: list[str]
    confidence_level: str
    status: str
    decided_by: str | None
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime
    candidate_request: DuplicateRequestSummary

    model_config = {"from_attributes": True}


class DuplicateDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class MergeDuplicateRequest(BaseModel):
    canonical_request_id: int
    candidate_id: int
    note: str | None = Field(default=None, max_length=500)


class DuplicateSummaryOut(UTCResponseModel):
    request_id: int
    canonical_request_id: int | None
    duplicate_state: str
    merged_report_count: int


class DemoIntakeBatch(BaseModel):
    reports: list[RescueRequestCreate] = Field(min_length=1, max_length=50)
    source: IntakeSource | None = None
    delay_ms: int = Field(default=0, ge=0, le=2_000)
