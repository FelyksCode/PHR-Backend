from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

import pytz
from sqlalchemy.orm import Session

from app.models.sync_job import SyncJob
from app.models.vendor_integration import VendorIntegration


class SyncJobService:
    def enqueue(
        self,
        db: Session,
        *,
        user_id: int,
        vendor: str,
        trigger: str = "manual",
        scheduled_at: Optional[datetime] = None,
    ) -> SyncJob:
        vendor_key = vendor.lower().strip()
        job = SyncJob(
            user_id=user_id,
            vendor=vendor_key,
            trigger=trigger,
            status="queued",
            scheduled_at=scheduled_at,
        )
        db.add(job)
        db.flush()  # ensures job.id is available

        integration = db.query(VendorIntegration).filter(
            VendorIntegration.user_id == user_id,
            VendorIntegration.vendor == vendor_key,
        ).first()
        if integration:
            integration.sync_status = "queued"
            integration.sync_job_id = job.id

        db.commit()
        db.refresh(job)
        return job

    def get_latest_job(
        self,
        db: Session,
        *,
        user_id: int,
        vendor: str,
    ) -> Optional[SyncJob]:
        vendor_key = vendor.lower().strip()
        return (
            db.query(SyncJob)
            .filter(SyncJob.user_id == user_id, SyncJob.vendor == vendor_key)
            .order_by(SyncJob.created_at.desc())
            .first()
        )

    def claim_next_queued_job(self, db: Session) -> Optional[SyncJob]:
        """Claim a queued job for execution.

        Uses an optimistic status transition to avoid double-processing.
        """
        job = (
            db.query(SyncJob)
            .filter(SyncJob.status == "queued")
            .order_by(SyncJob.created_at.asc())
            .first()
        )
        if not job:
            return None

        # Attempt to atomically transition queued -> running
        utc_now = datetime.now(pytz.UTC)
        updated = (
            db.query(SyncJob)
            .filter(SyncJob.id == job.id, SyncJob.status == "queued")
            .update({
                SyncJob.status: "running",
                SyncJob.started_at: utc_now,
                SyncJob.attempts: SyncJob.attempts + 1,
            })
        )
        if updated != 1:
            db.rollback()
            return None

        # Update integration metadata (best effort)
        integration = db.query(VendorIntegration).filter(
            VendorIntegration.user_id == job.user_id,
            VendorIntegration.vendor == job.vendor,
        ).first()
        if integration:
            integration.sync_status = "running"
            integration.sync_job_id = job.id

        db.commit()
        return db.query(SyncJob).filter(SyncJob.id == job.id).first()

    def mark_success(self, db: Session, *, job_id: str) -> None:
        utc_now = datetime.now(pytz.UTC)
        job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        if not job:
            return
        job.status = "success"
        job.finished_at = utc_now
        job.last_error = None

        integration = db.query(VendorIntegration).filter(
            VendorIntegration.user_id == job.user_id,
            VendorIntegration.vendor == job.vendor,
        ).first()
        if integration:
            integration.sync_status = "success"
            integration.sync_job_id = job.id
            integration.last_successful_sync_at = utc_now
            integration.last_sync_at = utc_now

        db.commit()

    def mark_failed(self, db: Session, *, job_id: str, error: str) -> None:
        utc_now = datetime.now(pytz.UTC)
        job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        if not job:
            return
        job.status = "failed"
        job.finished_at = utc_now
        job.last_error = error

        integration = db.query(VendorIntegration).filter(
            VendorIntegration.user_id == job.user_id,
            VendorIntegration.vendor == job.vendor,
        ).first()
        if integration:
            integration.sync_status = "failed"
            integration.sync_job_id = job.id

        db.commit()

    def maybe_enqueue_scheduled_jobs(self, db: Session, *, min_hours_between_runs: int) -> int:
        """Enqueue scheduled jobs for active integrations that are due."""
        utc = pytz.UTC
        now_utc = datetime.now(utc)
        due_before = now_utc - timedelta(hours=min_hours_between_runs)

        integrations = (
            db.query(VendorIntegration)
            .filter(VendorIntegration.is_active == True)
            .all()
        )

        enqueued = 0
        for integ in integrations:
            last_ok = integ.last_successful_sync_at
            if last_ok is not None and last_ok.tzinfo is None:
                last_ok = utc.localize(last_ok)

            if last_ok is not None and last_ok > due_before:
                continue

            # Skip if a job is already queued or running for this integration
            existing = (
                db.query(SyncJob)
                .filter(
                    SyncJob.user_id == integ.user_id,
                    SyncJob.vendor == integ.vendor,
                    SyncJob.status.in_(["queued", "running"]),
                )
                .first()
            )
            if existing:
                continue

            self.enqueue(db, user_id=integ.user_id, vendor=integ.vendor, trigger="scheduled")
            enqueued += 1

        return enqueued


sync_job_service = SyncJobService()
