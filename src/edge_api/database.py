"""
database.py — local storage for the edge node.

This is the heart of the "offline-first" idea. The edge node runs at the rural
site where the internet may be slow or absent. Every request is written to a
LOCAL SQLite file first, so nothing is ever lost while offline. The sync engine
later pushes those rows to the cloud when a connection is available.

SQLite is perfect here: it's a single file, needs no separate database server,
and is built into Python.
"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# The local database lives in a single file next to wherever we run the app.
SQLALCHEMY_DATABASE_URL = "sqlite:///./local_edge.db"

# NOTE: Gemini's draft called create_backend() — that function does not exist
# in SQLAlchemy and would crash on startup. The correct factory is create_engine().
# check_same_thread=False lets FastAPI's worker threads share the connection.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# A session is one "conversation" with the database. We make a factory here and
# hand out short-lived sessions per request (see get_db() in main.py).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that our table models inherit from.
Base = declarative_base()


class LocalQueue(Base):
    """One row = one captured payload waiting to be synced to the cloud."""

    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    payload_type = Column(String)   # e.g. "logistics_update", "service_request"
    data_payload = Column(String)   # the actual data, stored as a JSON string
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_synced = Column(Boolean, default=False)   # flipped to True once pushed to cloud


def init_db() -> None:
    """Create the database file and tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
