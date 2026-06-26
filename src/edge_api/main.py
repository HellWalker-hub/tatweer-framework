"""
main.py — the Sahar-Connect edge API.

Runs locally at the rural site (kiosk / edge node). Core flow:

    farmer raises an alert  ->  saved locally (never lost)  ->  nearest
    available responder computed instantly with Haversine  ->  dispatched

Run it with:
    uvicorn src.edge_api.main:app --reload
Interactive docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy.orm import Session

from .database import EmergencyAlert, ResponderNode, SessionLocal, init_db
from .routing import find_nearest_responder


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sahar-Connect Edge API", version="0.2.0", lifespan=lifespan)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- request/response models ----------------------------------------------
class AlertIn(BaseModel):
    # Accept both our short field names and Gemini's verbose ones, so either
    # dashboard payload shape works without an integration mismatch.
    farmer_name: str = "Anonymous Farmer"
    lat: float = Field(validation_alias=AliasChoices("lat", "latitude"))
    lon: float = Field(validation_alias=AliasChoices("lon", "longitude"))
    description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("description", "landmark_description"),
    )
    urgency: str = Field(  # "HIGH" | "CRITICAL"
        default="HIGH",
        validation_alias=AliasChoices("urgency", "urgency_level"),
    )


# --- endpoints -------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "online", "mode": "edge_node", "location": "Al Qua'a"}


@app.post("/alerts/create")
def create_alert(payload: AlertIn, db: Session = Depends(get_db)):
    """Log an emergency locally, then dispatch the nearest available responder."""
    alert = EmergencyAlert(
        farmer_name=payload.farmer_name,
        latitude=payload.lat,
        longitude=payload.lon,
        landmark_description=payload.description,
        urgency_level=payload.urgency,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    responders = (
        db.query(ResponderNode).filter(ResponderNode.is_available.is_(True)).all()
    )
    nearest, distance_km = find_nearest_responder(payload.lat, payload.lon, responders)

    return {
        "alert_id": alert.id,
        "status": "QUEUED_AND_DISPATCHED",
        "closest_responder": nearest.responder_name if nearest else "Broadcast to all neighbours",
        "responder_type": nearest.responder_type if nearest else None,
        "distance_km": round(distance_km, 2) if nearest else None,
    }


@app.get("/alerts")
def list_alerts(db: Session = Depends(get_db)):
    rows = db.query(EmergencyAlert).order_by(EmergencyAlert.id.desc()).all()
    return [
        {
            "id": a.id,
            "farmer_name": a.farmer_name,
            "lat": a.latitude,
            "lon": a.longitude,
            "landmark": a.landmark_description,
            "urgency": a.urgency_level,
            "timestamp": a.timestamp,
            "resolved": a.is_resolved,
            "synced": a.is_synced_to_cloud,
        }
        for a in rows
    ]


@app.get("/responders")
def list_responders(db: Session = Depends(get_db)):
    rows = db.query(ResponderNode).all()
    return [
        {
            "id": r.id,
            "name": r.responder_name,
            "type": r.responder_type,
            "lat": r.current_lat,
            "lon": r.current_lon,
            "available": r.is_available,
        }
        for r in rows
    ]


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(EmergencyAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    db.commit()
    return {"alert_id": alert_id, "status": "RESOLVED"}
