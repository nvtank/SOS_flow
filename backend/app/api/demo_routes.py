"""Demo-only multi-source intake endpoints. This router is not mounted outside DEMO_MODE."""

from time import sleep

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.rescue import DemoIntakeBatch, DemoScenarioControl, RescueRequestCreate, RescueRequestOut
from app.services.demo_scenario_service import inject_all, inject_next, pause_scenario, reset_scenario, scenario_status, set_scenario_speed, start_scenario
from app.services.intake_service import intake_rescue_request


router = APIRouter(prefix="/api/demo", tags=["demo simulator"])


def require_demo_token(x_demo_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.demo_mode or x_demo_token != settings.demo_token:
        raise HTTPException(status_code=404, detail="Demo simulator is unavailable")


@router.post("/intake", response_model=RescueRequestOut, dependencies=[Depends(require_demo_token)])
def demo_intake(payload: RescueRequestCreate, db: Session = Depends(get_db)):
    request, _ = intake_rescue_request(db, payload, simulated=True)
    return request


@router.post("/intake/batch", response_model=list[RescueRequestOut], dependencies=[Depends(require_demo_token)])
def demo_intake_batch(payload: DemoIntakeBatch, db: Session = Depends(get_db)):
    accepted: list[RescueRequestOut] = []
    for index, report in enumerate(payload.reports):
        if payload.source is not None:
            report.source = payload.source
        request, _ = intake_rescue_request(db, report, simulated=True)
        accepted.append(request)
        if payload.delay_ms and index < len(payload.reports) - 1:
            sleep(payload.delay_ms / 1000)
    return accepted


@router.get("/scenario", dependencies=[Depends(require_demo_token)])
def demo_scenario_status(db: Session = Depends(get_db)):
    return scenario_status(db)


@router.post("/scenario/start", dependencies=[Depends(require_demo_token)])
def demo_scenario_start(payload: DemoScenarioControl, db: Session = Depends(get_db)):
    return start_scenario(db, payload.speed)


@router.post("/scenario/pause", dependencies=[Depends(require_demo_token)])
def demo_scenario_pause(paused: bool = True, db: Session = Depends(get_db)):
    return pause_scenario(db, paused)


@router.post("/scenario/speed", dependencies=[Depends(require_demo_token)])
def demo_scenario_speed(payload: DemoScenarioControl, db: Session = Depends(get_db)):
    return set_scenario_speed(db, payload.speed)


@router.post("/scenario/next", dependencies=[Depends(require_demo_token)])
def demo_scenario_next(db: Session = Depends(get_db)):
    return inject_next(db)


@router.post("/scenario/all", dependencies=[Depends(require_demo_token)])
def demo_scenario_all(db: Session = Depends(get_db)):
    return inject_all(db)


@router.post("/scenario/reset", dependencies=[Depends(require_demo_token)])
def demo_scenario_reset(db: Session = Depends(get_db)):
    return reset_scenario(db)
