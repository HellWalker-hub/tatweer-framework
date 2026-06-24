"""
main.py — the edge API.

A small FastAPI app that runs locally at the rural site. Its job for now is
deliberately simple (this is our domain-agnostic "base idea"):

    capture a request  ->  save it locally  ->  let the sync engine push it later

Run it with:
    uvicorn src.edge_api.main:app --reload

Interactive docs are auto-generated at http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

import json

from .database import LocalQueue, SessionLocal, init_db


# lifespan replaces the deprecated @app.on_event("startup"). Code before `yield`
# runs once on startup; code after would run on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # make sure the local database/tables exist
    yield


app = FastAPI(
    title="Tatweer Rural Edge Framework",
    version="0.1.0",
    lifespan=lifespan,
)


def get_db():
    """Hand a fresh database session to a request, and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    """Quick liveness check — also used by the dashboard and (later) the cloud."""
    return {"status": "online", "mode": "edge_node", "location": "Al Qua'a"}


@app.post("/submit-request")
def submit_request(payload: dict, db: Session = Depends(get_db)):
    """
    Accept any payload and persist it locally so it is never lost, even with no
    internet. Expected shape:
        {"type": "service_request", "data": { ... }}
    """
    queue_item = LocalQueue(
        payload_type=payload.get("type", "generic"),
        data_payload=json.dumps(payload.get("data", {})),
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    return {"status": "saved_locally", "queue_id": queue_item.id}
