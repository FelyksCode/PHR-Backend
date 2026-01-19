from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SyncEnqueueResponse(BaseModel):
    vendor: str
    sync_job_id: str
    sync_status: str


class VendorSyncStatus(BaseModel):
    vendor: str
    vendor_user_id: Optional[str] = None
    last_successful_sync_at: Optional[datetime] = None
    sync_status: str
    sync_job_id: Optional[str] = None

    last_job_status: Optional[str] = None
    last_job_error: Optional[str] = None
    last_job_started_at: Optional[datetime] = None
    last_job_finished_at: Optional[datetime] = None


class SyncStatusResponse(BaseModel):
    user_id: int
    vendors: List[VendorSyncStatus]
