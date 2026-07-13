import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sosflow")

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
if settings.demo_mode:
    from app.api.demo_routes import router as demo_router

    app.include_router(demo_router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed_database(db)
    logger.info("SOSFlow API started")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
