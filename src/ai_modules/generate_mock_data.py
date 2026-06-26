"""
generate_mock_data.py — seed the local database with a realistic Al Qua'a scene.

This gives the routing engine real data to work against so our claims about
nearest-responder dispatch are *falsifiable* and demonstrable (Criterion 6).

It seeds:
  - 50 "neighbour" responder nodes scattered like camel farms around Al Qua'a,
  - a few "formal" responders (patrol / clinic / civil defence),
  - a couple of sample emergency alerts (one open, one resolved) for the demo.

Deterministic (fixed random seed) so results are reproducible. Re-running clears
and repopulates the responder/alert tables. Run with:

    python -m src.ai_modules.generate_mock_data
"""

import random

from src.edge_api.database import (
    EmergencyAlert,
    ResponderNode,
    SessionLocal,
    init_db,
)

# Al Qua'a sits in the Al Ain region, near the Tropic of Cancer.
# Approximate centre; farms are scattered within a ~30 km radius.
CENTER_LAT = 23.55
CENTER_LON = 55.50
SPREAD_DEG = 0.25  # ~25-28 km in this latitude band

random.seed(42)  # reproducible scene


def _scatter(center: float, spread: float) -> float:
    return round(center + random.uniform(-spread, spread), 5)


def seed(num_farms: int = 50) -> dict:
    init_db()
    db = SessionLocal()
    try:
        # Idempotent: clear previous mock data first.
        db.query(EmergencyAlert).delete()
        db.query(ResponderNode).delete()

        # 50 neighbour farms (the "ping nearest cluster of neighbours" network).
        for i in range(1, num_farms + 1):
            db.add(
                ResponderNode(
                    responder_name=f"Camel Farm {i:02d}",
                    responder_type="neighbour",
                    current_lat=_scatter(CENTER_LAT, SPREAD_DEG),
                    current_lon=_scatter(CENTER_LON, SPREAD_DEG),
                    is_available=random.random() > 0.2,  # ~80% available
                )
            )

        # A few formal responders, placed nearer the community centre.
        formal = [
            ("Al Ain Patrol", 0.05),
            ("Community Clinic Volunteer", 0.04),
            ("Civil Defence Unit", 0.06),
        ]
        for name, near in formal:
            db.add(
                ResponderNode(
                    responder_name=name,
                    responder_type="formal",
                    current_lat=_scatter(CENTER_LAT, near),
                    current_lon=_scatter(CENTER_LON, near),
                    is_available=True,
                )
            )

        # Sample alerts for the demo (one open, one already resolved).
        db.add(
            EmergencyAlert(
                farmer_name="Salem Al Qubaisi",
                latitude=_scatter(CENTER_LAT, SPREAD_DEG),
                longitude=_scatter(CENTER_LON, SPREAD_DEG),
                landmark_description="2km east of the water tower, vehicle stuck in dune",
                urgency_level="HIGH",
            )
        )
        db.add(
            EmergencyAlert(
                farmer_name="Mariam Farm",
                latitude=_scatter(CENTER_LAT, SPREAD_DEG),
                longitude=_scatter(CENTER_LON, SPREAD_DEG),
                landmark_description="Injured camel near the red dune ridge",
                urgency_level="CRITICAL",
                is_resolved=True,
            )
        )

        db.commit()

        counts = {
            "responders": db.query(ResponderNode).count(),
            "available": db.query(ResponderNode)
            .filter(ResponderNode.is_available.is_(True))
            .count(),
            "alerts": db.query(EmergencyAlert).count(),
        }
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    result = seed()
    print(
        f"[seed] populated Al Qua'a scene around ({CENTER_LAT}, {CENTER_LON}): "
        f"{result['responders']} responders "
        f"({result['available']} available), {result['alerts']} alerts."
    )
