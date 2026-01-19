"""Database model for queued vendor sync jobs.

This provides a lightweight, DB-backed job queue so that API endpoints can
signal a sync and return immediately, while a backend worker performs the
vendor ingestion.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vendor = Column(String, nullable=False, index=True)

    # manual | scheduled
    trigger = Column(String, nullable=False, default="manual")

    # queued | running | success | failed
    status = Column(String, nullable=False, default="queued", index=True)

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)

    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    last_error = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
