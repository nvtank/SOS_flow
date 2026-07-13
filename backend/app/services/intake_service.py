"""Common intake path for web reports and all simulated external sources."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.entities import RescueRequest
from app.schemas.rescue import RescueRequestCreate
from app.services.duplicate_service import detect_duplicate_candidates
from app.services.rescue_service import create_rescue_request
from app.services.silent_zone_service import note_report


SECRET_KEYS = {"authorization", "token", "password", "secret", "api_key", "access_token"}


def sanitize_raw_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SECRET_KEYS:
            continue
        if isinstance(value, dict):
            cleaned[key] = sanitize_raw_payload(value)
        elif isinstance(value, list):
            cleaned[key] = [sanitize_raw_payload(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
    return cleaned


def intake_rescue_request(db: Session, payload: RescueRequestCreate, *, simulated: bool = False) -> tuple[RescueRequest, bool]:
    """Idempotently intake every source through the same create/analyze/priority flow."""
    predicates = []
    if payload.client_submission_id:
        predicates.append(RescueRequest.client_submission_id == payload.client_submission_id)
    if payload.external_reference:
        predicates.append(
            and_(RescueRequest.source == payload.source.value, RescueRequest.external_reference == payload.external_reference)
        )
    if predicates:
        existing = db.scalar(select(RescueRequest).where(or_(*predicates)).order_by(RescueRequest.id.asc()))
        if existing:
            return existing, True

    payload.raw_payload = sanitize_raw_payload(payload.raw_payload)
    payload.is_simulated = simulated
    try:
        request = create_rescue_request(db, payload)
    except HTTPException as exc:
        # A concurrent submission can pass the initial lookup then lose the DB
        # unique-index race. Read the winner and preserve idempotent semantics.
        if exc.status_code == 409 and predicates:
            existing = db.scalar(select(RescueRequest).where(or_(*predicates)).order_by(RescueRequest.id.asc()))
            if existing:
                return existing, True
        raise
    note_report(db, request.latitude, request.longitude, request.received_at)
    db.commit()
    detect_duplicate_candidates(db, request)
    db.refresh(request)
    return request, False
