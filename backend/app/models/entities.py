from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RequestStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    RESCUING = "RESCUING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MissionStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    RESCUING = "RESCUING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TeamStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class RescueRequest(Base):
    __tablename__ = "rescue_requests"

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
    source: Mapped[str] = mapped_column(String(40), default="WEB")
    ai_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    priority_level: Mapped[str] = mapped_column(String(20), default="LOW", index=True)
    priority_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default=RequestStatus.PENDING_VERIFICATION.value, index=True)
    assigned_team_id: Mapped[int | None] = mapped_column(ForeignKey("rescue_teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_team: Mapped["RescueTeam | None"] = relationship(back_populates="requests")
    missions: Mapped[list["RescueMission"]] = relationship(back_populates="request")


class RescueTeam(Base):
    __tablename__ = "rescue_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=4)
    vehicle_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TeamStatus.AVAILABLE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requests: Mapped[list[RescueRequest]] = relationship(back_populates="assigned_team")
    missions: Mapped[list["RescueMission"]] = relationship(back_populates="team")


class RescueMission(Base):
    __tablename__ = "rescue_missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("rescue_teams.id"))
    status: Mapped[str] = mapped_column(String(40), default=MissionStatus.ASSIGNED.value)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    request: Mapped[RescueRequest] = relationship(back_populates="missions")
    team: Mapped[RescueTeam] = relationship(back_populates="missions")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("rescue_requests.id"))
    old_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40))
    changed_by: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
