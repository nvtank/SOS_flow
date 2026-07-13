from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
    source: str = "WEB"
    note: str | None = None


class RescueTeamOut(BaseModel):
    id: int
    name: str
    phone_number: str | None
    member_count: int
    vehicle_type: str | None
    latitude: float | None
    longitude: float | None
    status: str

    model_config = {"from_attributes": True}


class RescueRequestOut(BaseModel):
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
    ai_analysis: dict[str, Any]
    priority_score: int
    priority_level: str
    priority_reasons: list[str]
    status: str
    assigned_team_id: int | None
    assigned_team: RescueTeamOut | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequestStatusOut(BaseModel):
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
    latitude: float | None = None
    longitude: float | None = None
    status: str = "AVAILABLE"


class MissionOut(BaseModel):
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


class StatisticsOut(BaseModel):
    total_requests: int
    critical_requests: int
    pending_requests: int
    active_rescues: int
    completed_requests: int
    available_teams: int
