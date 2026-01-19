"""Vendor-agnostic sync signaling + read-only status endpoints.

This router enforces the architecture rule:
- UI can request a sync (signal) and read status/results.
- Vendor API pulling happens only in backend worker jobs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import httpx

from app.auth.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.vendor_integration import VendorIntegration
from app.config import settings
from app.schemas.vendor import HealthObservationsResponse, HealthObservation
from app.schemas.sync import SyncEnqueueResponse, SyncStatusResponse, VendorSyncStatus
from app.services.sync_job_service import sync_job_service

router = APIRouter(tags=["sync"])


@router.post("/vendors/{vendor}/sync", status_code=status.HTTP_202_ACCEPTED, response_model=SyncEnqueueResponse)
async def enqueue_vendor_sync(
    vendor: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor_key = vendor.lower().strip()

    # Ensure the integration exists and is active; do NOT call vendor APIs here.
    integration = (
        db.query(VendorIntegration)
        .filter(
            VendorIntegration.user_id == current_user.id,
            VendorIntegration.vendor == vendor_key,
        )
        .first()
    )
    if not integration or not integration.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active vendor integration found",
        )

    # Enqueue a job and return immediately.
    job = sync_job_service.enqueue(db, user_id=current_user.id, vendor=vendor_key, trigger="manual")

    return SyncEnqueueResponse(vendor=vendor_key, sync_job_id=job.id, sync_status="queued")


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    vendor: Optional[str] = None,
):
    q = db.query(VendorIntegration).filter(VendorIntegration.user_id == current_user.id)
    if vendor:
        q = q.filter(VendorIntegration.vendor == vendor.lower().strip())

    integrations = q.all()
    vendors = []
    for integ in integrations:
        latest = sync_job_service.get_latest_job(db, user_id=current_user.id, vendor=integ.vendor)
        vendors.append(
            VendorSyncStatus(
                vendor=integ.vendor,
                vendor_user_id=integ.vendor_user_id,
                last_successful_sync_at=integ.last_successful_sync_at,
                sync_status=integ.sync_status,
                sync_job_id=integ.sync_job_id,
                last_job_status=(latest.status if latest else None),
                last_job_error=(latest.last_error if latest else None),
                last_job_started_at=(latest.started_at if latest else None),
                last_job_finished_at=(latest.finished_at if latest else None),
            )
        )

    return SyncStatusResponse(user_id=current_user.id, vendors=vendors)


@router.get("/observations", response_model=HealthObservationsResponse)
async def get_observations(
    page: int = 1,
    page_size: int = 20,
    observation_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only observations endpoint for Flutter.

    This intentionally does not trigger vendor ingestion.
    """

    if not current_user.fhir_patient_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have a FHIR patient record",
        )

    params = {
        "patient": current_user.fhir_patient_id,
        "_count": page_size,
        "_offset": (page - 1) * page_size,
        "_sort": "-date",
    }

    if date_from:
        params["date"] = f"ge{date_from}"
    if date_to:
        date_param = params.get("date", "")
        if date_param:
            params["date"] = f"{date_param}&date=le{date_to}"
        else:
            params["date"] = f"le{date_to}"

    if observation_type:
        type_to_loinc = {
            "heart_rate": "8867-4",
            "spo2": "59408-5",
            "body_weight": "29463-7",
            "steps": "41950-7",
            "calories": "41981-2",
            "distance": "41953-1",
        }
        if observation_type in type_to_loinc:
            params["code"] = f"http://loinc.org|{type_to_loinc[observation_type]}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.fhir_base_url}/Observation",
                params=params,
                timeout=30.0,
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve health observations from FHIR server",
                )
            bundle = response.json()

        observations = []
        entries = bundle.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Observation":
                continue
            try:
                code_coding = resource.get("code", {}).get("coding", [{}])[0]
                value_quantity = resource.get("valueQuantity", {})
                observations.append(
                    HealthObservation(
                        id=resource.get("id", ""),
                        code=code_coding.get("code", ""),
                        code_system=code_coding.get("system", ""),
                        display=code_coding.get("display", ""),
                        value=value_quantity.get("value", 0),
                        unit=value_quantity.get("unit", ""),
                        effective_datetime=resource.get("effectiveDateTime", ""),
                        patient_id=current_user.fhir_patient_id,
                    )
                )
            except Exception:
                continue

        total = bundle.get("total", len(observations))
        has_more = total > (page * page_size)
        return HealthObservationsResponse(
            observations=observations,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to FHIR server: {str(e)}",
        )
