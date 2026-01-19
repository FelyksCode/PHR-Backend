from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import pytz

from app.config import settings
from app.database import SessionLocal
from app.models.sync_job import SyncJob
from app.models.user import User
from app.models.vendor_integration import VendorIntegration
from app.services.ingestion.registry import ingestion_registry
from app.services.sync_job_service import sync_job_service

logger = logging.getLogger(__name__)


class SyncWorker:
    def __init__(self) -> None:
        self._stop = asyncio.Event()
        self._last_schedule_tick_at: datetime | None = None

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        logger.info("SyncWorker started")
        utc = pytz.UTC

        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    # Periodically enqueue scheduled syncs.
                    now = datetime.now(utc)
                    if (
                        self._last_schedule_tick_at is None
                        or (now - self._last_schedule_tick_at).total_seconds() >= settings.sync_schedule_tick_seconds
                    ):
                        self._last_schedule_tick_at = now
                        try:
                            enq = sync_job_service.maybe_enqueue_scheduled_jobs(
                                db,
                                min_hours_between_runs=settings.sync_scheduled_min_hours_between_runs,
                            )
                            if enq:
                                logger.info(f"Enqueued {enq} scheduled sync job(s)")
                        except Exception:
                            logger.exception("Failed while enqueueing scheduled jobs")

                    # Claim next queued job (manual or scheduled)
                    job = sync_job_service.claim_next_queued_job(db)

                if not job:
                    await asyncio.sleep(settings.sync_poll_interval_seconds)
                    continue

                # Execute outside the transaction/session used for claiming
                with SessionLocal() as exec_db:
                    await self._execute_job(exec_db, job_id=job.id)

            except Exception:
                logger.exception("SyncWorker loop error")
                await asyncio.sleep(settings.sync_poll_interval_seconds)

        logger.info("SyncWorker stopped")

    async def _execute_job(self, db, *, job_id: str) -> None:
        job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        # If job isn't found, just no-op.
        if not job:
            return

        try:
            user = db.query(User).filter(User.id == job.user_id).first()
            if not user:
                sync_job_service.mark_failed(db, job_id=job.id, error="User not found")
                return

            integration = (
                db.query(VendorIntegration)
                .filter(VendorIntegration.user_id == user.id, VendorIntegration.vendor == job.vendor)
                .first()
            )
            if not integration or not integration.is_active:
                sync_job_service.mark_failed(db, job_id=job.id, error="No active vendor integration")
                return

            svc = ingestion_registry.get(job.vendor)
            after_dt = integration.last_successful_sync_at
            if after_dt is None:
                # Fallback to legacy field if present
                after_dt = integration.last_sync_at

            result = await svc.ingest(db=db, user=user, integration=integration, after_datetime=after_dt)
            if result.get("success"):
                sync_job_service.mark_success(db, job_id=job.id)
            else:
                err = "; ".join(result.get("errors") or []) or "Ingestion failed"
                sync_job_service.mark_failed(db, job_id=job.id, error=err)

        except Exception as e:
            sync_job_service.mark_failed(db, job_id=job.id, error=str(e))


sync_worker = SyncWorker()
