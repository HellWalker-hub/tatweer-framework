"""
database.py — local storage for the Sahar-Connect edge node.

Offline-first: every emergency alert is written to a LOCAL SQLite file the
instant it arrives, so nothing is lost when the desert cellular signal drops.
The sync engine pushes alerts to the cloud later, when a connection exists.

Two tables:
  - EmergencyAlert : a request for help (farmer pings location + landmark).
  - ResponderNode  : a registered neighbour / formal responder who can help.
"""

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./local_edge.db"

# create_engine (NOT create_backend — that function doesn't exist in SQLAlchemy).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EmergencyAlert(Base):
    """One call for help raised by a resident/farmer in the community."""

    __tablename__ = "emergency_alerts"

    id = Column(Integer, primary_key=True, index=True)
    farmer_name = Column(String, default="Anonymous Farmer")
    latitude = Column(Float)
    longitude = Column(Float)
    landmark_description = Column(String, nullable=True)  # e.g. "3km N of Red Dune"
    urgency_level = Column(String)                        # "HIGH" | "CRITICAL"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    is_synced_to_cloud = Column(Boolean, default=False)


class ResponderNode(Base):
    """A neighbour or formal responder who can be dispatched to an alert."""

    __tablename__ = "responder_nodes"

    id = Column(Integer, primary_key=True, index=True)
    responder_name = Column(String)          # "Camel Farm 12", "Al Ain Patrol"
    responder_type = Column(String, default="neighbour")  # "neighbour" | "formal"
    current_lat = Column(Float)
    current_lon = Column(Float)
    is_available = Column(Boolean, default=True)


def init_db() -> None:
    """Create the database file and tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
