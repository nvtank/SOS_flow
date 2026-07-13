from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.time import utc_now


class RequestStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    RESCUING = "RESCUING"
    BLOCKED = "BLOCKED"
    NEED_REINFORCEMENT = "NEED_REINFORCEMENT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MissionStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    RESCUING = "RESCUING"
    BLOCKED = "BLOCKED"
    NEED_REINFORCEMENT = "NEED_REINFORCEMENT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TeamStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class IntakeSource(str, Enum):
    WEB = "WEB"
    CALL_112 = "CALL_112"
    PHONE = "PHONE"
    SMS = "SMS"
    ZALO = "ZALO"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    LOCAL_OFFICER = "LOCAL_OFFICER"
    OFFLINE_SYNC = "OFFLINE_SYNC"


class DuplicateState(str, Enum):
    NOT_DUPLICATE = "NOT_DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"


class SilentZoneVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFYING = "VERIFYING"
    SAFE = "SAFE"
    NEED_RESCUE = "NEED_RESCUE"


class RescueRequest(Base):
    __tablename__ = "rescue_requests"
    __table_args__ = (
        Index("ix_rescue_requests_source", "source"),
        Index("ix_rescue_requests_assigned_team_id", "assigned_team_id"),
        Index(
            "uq_rescue_requests_client_submission_id",
            "client_submission_id",
            unique=True,
            sqlite_where=text("client_submission_id IS NOT NULL"),
            postgresql_where=text("client_submission_id IS NOT NULL"),
        ),
        Index(
            "uq_rescue_requests_source_external_reference",
            "source",
            "external_reference",
            unique=True,
            sqlite_where=text("external_reference IS NOT NULL"),
            postgresql_where=text("external_reference IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    number_of_people: Mapped[int] = mapped_column(Integer, default=1)
    number_of_children: Mapped[int] = mapped_column(Integer, default=0)
    number_of_elderly: Mapped[int] = mapped_column(Integer, default=0)
    number_of_injured: Mapped[int] = mapped_column(Integer, default=0)
    has_disabled_person: Mapped[bool] = mapped_column(Boolean, default=False)
    has_pregnant_person: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trapped: Mapped[bool] = mapped_column(Boolean, default=False)
    water_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default=IntakeSource.WEB.value)
    external_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    client_submission_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    priority_level: Mapped[str] = mapped_column(String(20), default="LOW", index=True)
    priority_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default=RequestStatus.PENDING_VERIFICATION.value, index=True)
    assigned_team_id: Mapped[int | None] = mapped_column(ForeignKey("rescue_teams.id"), nullable=True)
    canonical_request_id: Mapped[int | None] = mapped_column(ForeignKey("rescue_requests.id"), nullable=True)
    duplicate_state: Mapped[str] = mapped_column(String(32), default=DuplicateState.NOT_DUPLICATE.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    priority_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    assigned_team: Mapped["RescueTeam | None"] = relationship(back_populates="requests")
    missions: Mapped[list["RescueMission"]] = relationship(back_populates="request", cascade="all, delete-orphan")
    status_history: Mapped[list["StatusHistory"]] = relationship(back_populates="request", order_by="StatusHistory.created_at", cascade="all, delete-orphan")
    canonical_request: Mapped["RescueRequest | None"] = relationship(
        remote_side="RescueRequest.id", back_populates="merged_reports", foreign_keys=[canonical_request_id]
    )
    merged_reports: Mapped[list["RescueRequest"]] = relationship(back_populates="canonical_request")
    duplicate_candidates: Mapped[list["DuplicateCandidate"]] = relationship(
        foreign_keys="DuplicateCandidate.request_id", back_populates="request", cascade="all, delete-orphan"
    )
    duplicate_matches: Mapped[list["DuplicateCandidate"]] = relationship(
        foreign_keys="DuplicateCandidate.candidate_request_id", back_populates="candidate_request", cascade="all, delete-orphan"
    )


class RescueStation(Base):
    """A fixed operational base, not a live GPS position."""

    __tablename__ = "rescue_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    area_code: Mapped[str] = mapped_column(String(32), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    teams: Mapped[list["RescueTeam"]] = relationship(back_populates="station")


class RescueTeam(Base):
    __tablename__ = "rescue_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=4)
    vehicle_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    equipment: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_people_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("rescue_stations.id"), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_mission_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=TeamStatus.AVAILABLE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    requests: Mapped[list[RescueRequest]] = relationship(back_populates="assigned_team")
    missions: Mapped[list["RescueMission"]] = relationship(back_populates="team")
    station: Mapped["RescueStation | None"] = relationship(back_populates="teams")


class RescueMission(Base):
    __tablename__ = "rescue_missions"
    __table_args__ = (
        Index(
            "uq_active_mission_per_request",
            "request_id",
            unique=True,
            sqlite_where=text("status NOT IN ('COMPLETED', 'FAILED')"),
            postgresql_where=text("status NOT IN ('COMPLETED', 'FAILED')"),
        ),
        Index(
            "uq_active_mission_per_team",
            "team_id",
            unique=True,
            sqlite_where=text("status NOT IN ('COMPLETED', 'FAILED')"),
            postgresql_where=text("status NOT IN ('COMPLETED', 'FAILED')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("rescue_teams.id"))
    status: Mapped[str] = mapped_column(String(40), default=MissionStatus.ASSIGNED.value)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    request: Mapped[RescueRequest] = relationship(back_populates="missions")
    team: Mapped[RescueTeam] = relationship(back_populates="missions")
    events: Mapped[list["MissionEvent"]] = relationship(back_populates="mission", order_by="MissionEvent.created_at", cascade="all, delete-orphan")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"))
    old_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40))
    changed_by: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    request: Mapped[RescueRequest] = relationship(back_populates="status_history")


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (
        UniqueConstraint("request_id", "candidate_request_id", name="uq_duplicate_candidate_pair"),
        Index("ix_duplicate_candidates_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"), index=True)
    candidate_request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"), index=True)
    duplicate_score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_level: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(32), default=DuplicateState.POSSIBLE_DUPLICATE.value)
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    request: Mapped[RescueRequest] = relationship(foreign_keys=[request_id], back_populates="duplicate_candidates")
    candidate_request: Mapped[RescueRequest] = relationship(foreign_keys=[candidate_request_id], back_populates="duplicate_matches")


class MissionEvent(Base):
    __tablename__ = "mission_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("rescue_missions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped[RescueMission] = relationship(back_populates="events")


class SilentZone(Base):
    __tablename__ = "silent_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    scenario_key: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_meters: Mapped[int] = mapped_column(Integer, default=1000)
    hazard_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    silence_threshold_minutes: Mapped[int] = mapped_column(Integer, default=30)
    verification_status: Mapped[str] = mapped_column(String(32), default=SilentZoneVerificationStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    history: Mapped[list["SilentZoneHistory"]] = relationship(back_populates="zone", cascade="all, delete-orphan", order_by="SilentZoneHistory.created_at")


class SilentZoneHistory(Base):
    __tablename__ = "silent_zone_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("silent_zones.id"), index=True)
    old_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    zone: Mapped[SilentZone] = relationship(back_populates="history")


class DemoScenarioState(Base):
    __tablename__ = "demo_scenario_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    next_event: Mapped[int] = mapped_column(Integer, default=0)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    speed: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
