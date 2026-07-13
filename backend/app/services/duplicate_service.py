"""Explainable duplicate suggestions for the MVP; no embeddings or auto-merges."""

from difflib import SequenceMatcher
from math import asin, cos, radians, sin, sqrt
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.time import as_utc, utc_now
from app.models.entities import DuplicateCandidate, DuplicateState, RescueRequest, StatusHistory


POSSIBLE_DUPLICATE_THRESHOLD = 0.55


def normalize_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"[^a-z0-9\s]", " ", normalized).strip()


def _distance_meters(first: RescueRequest, second: RescueRequest) -> float | None:
    if None in (first.latitude, first.longitude, second.latitude, second.longitude):
        return None
    lat1, lon1, lat2, lon2 = map(radians, (first.latitude, first.longitude, second.latitude, second.longitude))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(a))


def _shared_location_terms(first: RescueRequest, second: RescueRequest) -> list[str]:
    stop_words = {"nguoi", "dang", "can", "cuu", "voi", "nha", "nuoc", "chung", "toi", "bao", "o", "co"}
    first_terms = {term for term in normalize_text(f"{first.address or ''} {first.message}").split() if len(term) >= 4 and term not in stop_words}
    second_terms = {term for term in normalize_text(f"{second.address or ''} {second.message}").split() if len(term) >= 4 and term not in stop_words}
    return sorted(first_terms & second_terms)


def score_duplicate(first: RescueRequest, second: RescueRequest) -> dict:
    """Return an additive, human-explainable score in the 0..1 range."""
    score = 0.0
    reasons: list[str] = []
    distance = _distance_meters(first, second)
    if distance is not None:
        if distance <= 250:
            score += 0.35
            reasons.append(f"Hai báo cáo cách nhau {round(distance):d} m")
        elif distance <= 1_000:
            score += 0.15
            reasons.append(f"Hai báo cáo cùng khu vực, cách nhau {round(distance):d} m")

    minutes_apart = abs((as_utc(first.received_at) - as_utc(second.received_at)).total_seconds()) / 60
    if minutes_apart <= 10:
        score += 0.15
        reasons.append(f"Được gửi cách nhau {round(minutes_apart):d} phút")
    elif minutes_apart <= 30:
        score += 0.07
        reasons.append(f"Được gửi trong cùng khoảng thời gian ({round(minutes_apart):d} phút)")

    first_address, second_address = normalize_text(first.address), normalize_text(second.address)
    if first_address and first_address == second_address:
        score += 0.20
        reasons.append("Địa chỉ đã chuẩn hóa trùng nhau")
    elif first_address and second_address and SequenceMatcher(None, first_address, second_address).ratio() >= 0.72:
        score += 0.10
        reasons.append("Địa chỉ đã chuẩn hóa gần giống nhau")

    if first.phone_number and first.phone_number == second.phone_number:
        score += 0.25
        reasons.append("Cùng số điện thoại người báo")

    similarity = SequenceMatcher(None, normalize_text(first.message), normalize_text(second.message)).ratio()
    if similarity >= 0.45:
        score += similarity * 0.25
        reasons.append(f"Nội dung giống nhau {round(similarity * 100):d}%")

    first_risks = set((first.ai_analysis or {}).get("detected_risks", []))
    second_risks = set((second.ai_analysis or {}).get("detected_risks", []))
    if first_risks & second_risks:
        score += 0.10
        reasons.append("Cùng tín hiệu rủi ro: " + ", ".join(sorted(first_risks & second_risks)))

    shared_terms = _shared_location_terms(first, second)
    if shared_terms:
        reasons.append("Cùng nhắc đến: " + ", ".join(shared_terms[:3]))

    score = round(min(score, 1.0), 2)
    confidence = "HIGH" if score >= 0.75 else "MEDIUM" if score >= POSSIBLE_DUPLICATE_THRESHOLD else "LOW"
    return {"duplicate_score": score, "reasons": reasons, "confidence_level": confidence}


def detect_duplicate_candidates(db: Session, request: RescueRequest) -> list[DuplicateCandidate]:
    """Store suggestions only. This function never changes canonical ownership."""
    others = db.scalars(select(RescueRequest).where(RescueRequest.id != request.id)).all()
    created: list[DuplicateCandidate] = []
    for other in others:
        result = score_duplicate(request, other)
        if result["duplicate_score"] < POSSIBLE_DUPLICATE_THRESHOLD:
            continue
        candidate = DuplicateCandidate(request_id=request.id, candidate_request_id=other.id, status=DuplicateState.POSSIBLE_DUPLICATE.value, **result)
        db.add(candidate)
        request.duplicate_state = DuplicateState.POSSIBLE_DUPLICATE.value
        other.duplicate_state = DuplicateState.POSSIBLE_DUPLICATE.value
        created.append(candidate)
    if created:
        db.commit()
    return created


def list_duplicate_candidates(db: Session, request_id: int) -> list[DuplicateCandidate]:
    if not db.get(RescueRequest, request_id):
        raise HTTPException(status_code=404, detail="Rescue request not found")
    return db.scalars(
        select(DuplicateCandidate)
        .options(joinedload(DuplicateCandidate.candidate_request))
        .where(DuplicateCandidate.request_id == request_id)
        .order_by(DuplicateCandidate.duplicate_score.desc(), DuplicateCandidate.created_at.desc())
    ).all()


def _candidate_for_request(db: Session, request_id: int, candidate_id: int) -> DuplicateCandidate:
    candidate = db.scalar(
        select(DuplicateCandidate)
        .options(joinedload(DuplicateCandidate.request), joinedload(DuplicateCandidate.candidate_request))
        .where(DuplicateCandidate.id == candidate_id, DuplicateCandidate.request_id == request_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Duplicate candidate not found for this request")
    return candidate


def _record_duplicate_audit(db: Session, request: RescueRequest, note: str) -> None:
    db.add(StatusHistory(request_id=request.id, old_status=request.status, new_status=request.status, changed_by="admin", note=note))


def decide_duplicate(db: Session, request_id: int, candidate_id: int, confirmed: bool, note: str | None = None) -> DuplicateCandidate:
    candidate = _candidate_for_request(db, request_id, candidate_id)
    candidate.status = DuplicateState.CONFIRMED_DUPLICATE.value if confirmed else DuplicateState.NOT_DUPLICATE.value
    candidate.decided_by = "admin"
    candidate.decision_note = note
    candidate.decided_at = utc_now()
    if confirmed:
        candidate.request.duplicate_state = DuplicateState.CONFIRMED_DUPLICATE.value
        candidate.candidate_request.duplicate_state = DuplicateState.CONFIRMED_DUPLICATE.value
        audit_note = f"Duplicate candidate #{candidate.id} confirmed" + (f": {note}" if note else "")
    else:
        recalculate_duplicate_state(db, candidate.request)
        recalculate_duplicate_state(db, candidate.candidate_request)
        audit_note = f"Duplicate candidate #{candidate.id} rejected" + (f": {note}" if note else "")
    _record_duplicate_audit(db, candidate.request, audit_note)
    db.commit()
    db.refresh(candidate)
    return candidate


def recalculate_duplicate_state(db: Session, request: RescueRequest) -> None:
    has_confirmed = db.scalar(
        select(DuplicateCandidate.id).where(
            or_(DuplicateCandidate.request_id == request.id, DuplicateCandidate.candidate_request_id == request.id),
            DuplicateCandidate.status == DuplicateState.CONFIRMED_DUPLICATE.value,
        ).limit(1)
    )
    has_possible = db.scalar(
        select(DuplicateCandidate.id).where(
            or_(DuplicateCandidate.request_id == request.id, DuplicateCandidate.candidate_request_id == request.id),
            DuplicateCandidate.status == DuplicateState.POSSIBLE_DUPLICATE.value,
        ).limit(1)
    )
    request.duplicate_state = (
        DuplicateState.CONFIRMED_DUPLICATE.value if has_confirmed else DuplicateState.POSSIBLE_DUPLICATE.value if has_possible else DuplicateState.NOT_DUPLICATE.value
    )


def merge_duplicate_report(db: Session, request_id: int, canonical_request_id: int, candidate_id: int, note: str | None = None) -> RescueRequest:
    candidate = _candidate_for_request(db, request_id, candidate_id)
    if candidate.status != DuplicateState.CONFIRMED_DUPLICATE.value:
        raise HTTPException(status_code=409, detail="Confirm the duplicate candidate before merging")
    canonical = db.get(RescueRequest, canonical_request_id)
    if not canonical or canonical.id == request_id:
        raise HTTPException(status_code=422, detail="A different canonical request is required")
    if candidate.candidate_request_id != canonical.id:
        raise HTTPException(status_code=422, detail="Canonical request must match the confirmed duplicate candidate")

    # Merge into the root canonical incident without deleting or mutating the report's lifecycle.
    while canonical.canonical_request_id is not None:
        canonical = canonical.canonical_request
    candidate.request.canonical_request_id = canonical.id
    candidate.request.duplicate_state = DuplicateState.CONFIRMED_DUPLICATE.value
    candidate.decision_note = "\n".join(filter(None, [candidate.decision_note, note, f"Merged into {canonical.request_code}"]))
    _record_duplicate_audit(db, candidate.request, f"Report merged into canonical incident {canonical.request_code}" + (f": {note}" if note else ""))
    _record_duplicate_audit(db, canonical, f"Merged duplicate report {candidate.request.request_code}" + (f": {note}" if note else ""))
    db.commit()
    db.refresh(candidate.request)
    return candidate.request


def duplicate_summary(db: Session, request_id: int) -> dict:
    request = db.get(RescueRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")
    canonical_id = request.canonical_request_id or request.id
    merged_count = db.scalar(select(func.count(RescueRequest.id)).where(RescueRequest.canonical_request_id == canonical_id))
    return {
        "request_id": request.id,
        "canonical_request_id": request.canonical_request_id,
        "duplicate_state": request.duplicate_state,
        "merged_report_count": merged_count or 0,
    }
