"""Health data endpoints - vendor-agnostic API for consuming health observations."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import httpx
from datetime import date

from app.database import get_db
from app.auth.auth import get_current_user
from app.models.user import User
from app.config import settings
from app.schemas.vendor import HealthObservationsResponse, HealthObservation
from app.services.sync_job_service import sync_job_service
from app.services.vendor_integration_service import vendor_integration_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"]
)


@router.get("/observations", response_model=HealthObservationsResponse)
async def get_health_observations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    observation_type: Optional[str] = Query(None, description="Filter by observation type (e.g., heart_rate, spo2)"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get health observations for the authenticated user
    
    Returns vendor-agnostic FHIR Observation data from the FHIR server.
    Supports pagination and filtering.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        observation_type: Filter by specific observation type
        date_from: Filter observations from this date
        date_to: Filter observations until this date
        current_user: Authenticated user
        db: Database session
        
    Returns:
        HealthObservationsResponse with paginated observations
    """
    # Check if user has FHIR patient ID
    if not current_user.fhir_patient_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have a FHIR patient record"
        )
    
    # Build FHIR search parameters
    params = {
        "patient": current_user.fhir_patient_id,
        "_count": page_size,
        "_offset": (page - 1) * page_size,
        "_sort": "-date"  # Sort by date descending
    }
    
    # Add date filters if provided
    if date_from:
        params["date"] = f"ge{date_from}"
    if date_to:
        date_param = params.get("date", "")
        if date_param:
            params["date"] = f"{date_param}&date=le{date_to}"
        else:
            params["date"] = f"le{date_to}"
    
    # Add code filter if observation type provided
    if observation_type:
        # Map common types to LOINC codes
        type_to_loinc = {
            "heart_rate": "8867-4",
            "spo2": "59408-5",
            "body_weight": "29463-7",
            "steps": "41950-7",
            "calories": "41981-2",
            "distance": "41953-1"
        }
        
        if observation_type in type_to_loinc:
            params["code"] = f"http://loinc.org|{type_to_loinc[observation_type]}"
    
    try:
        # Query FHIR server
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.fhir_base_url}/Observation",
                params=params,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"FHIR query failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve health observations from FHIR server"
                )
            
            bundle = response.json()
        
        # Parse FHIR Bundle
        observations = []
        entries = bundle.get("entry", [])
        
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Observation":
                try:
                    # Extract observation data
                    code_coding = resource.get("code", {}).get("coding", [{}])[0]
                    value_quantity = resource.get("valueQuantity", {})
                    
                    obs = HealthObservation(
                        id=resource.get("id", ""),
                        code=code_coding.get("code", ""),
                        code_system=code_coding.get("system", ""),
                        display=code_coding.get("display", ""),
                        value=value_quantity.get("value", 0),
                        unit=value_quantity.get("unit", ""),
                        effective_datetime=resource.get("effectiveDateTime", ""),
                        patient_id=current_user.fhir_patient_id
                    )
                    observations.append(obs)
                except Exception as e:
                    logger.warning(f"Failed to parse observation: {str(e)}")
                    continue
        
        # Get total count
        total = bundle.get("total", len(observations))
        has_more = total > (page * page_size)
        
        return HealthObservationsResponse(
            observations=observations,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error querying FHIR server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to FHIR server: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving observations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.post("/sync")
async def sync_health_data(
    date_str: Optional[str] = Query(None, description="Date to sync (YYYY-MM-DD), defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a sync of health data from connected vendors
    
    Fetches latest data from all connected vendors and stores as FHIR Observations.
    The sync happens in the background.
    
    Args:
        background_tasks: FastAPI background tasks
        date_str: Specific date to sync (optional)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Sync initiated message
    """
    # Validate date format if provided
    if date_str:
        try:
            date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Architecture rule: do not pull vendor APIs inline.
    # Enqueue vendor sync jobs and return immediately.
    integrations = vendor_integration_service.get_user_integrations(db=db, user_id=current_user.id, active_only=True)
    job_ids = []
    for integ in integrations:
        job = sync_job_service.enqueue(db, user_id=current_user.id, vendor=integ.vendor, trigger="manual")
        job_ids.append({"vendor": integ.vendor, "sync_job_id": job.id})

    return {
        "message": "Health data sync enqueued",
        "user_id": current_user.id,
        "date": date_str or date.today().isoformat(),
        "jobs": job_ids,
    }


@router.post("/sync/immediate")
async def sync_health_data_immediate(
    date_str: Optional[str] = Query(None, description="Date to sync (YYYY-MM-DD), defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger an immediate sync of health data from connected vendors
    
    Fetches latest data from all connected vendors and stores as FHIR Observations.
    This endpoint waits for the sync to complete before returning.
    
    Args:
        date_str: Specific date to sync (optional)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Sync results
    """
    # Validate date format if provided
    if date_str:
        try:
            date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Kept for backward compatibility, but now behaves like an enqueue-only signal.
    integrations = vendor_integration_service.get_user_integrations(db=db, user_id=current_user.id, active_only=True)
    job_ids = []
    for integ in integrations:
        job = sync_job_service.enqueue(db, user_id=current_user.id, vendor=integ.vendor, trigger="manual")
        job_ids.append({"vendor": integ.vendor, "sync_job_id": job.id})

    return {
        "message": "Health data sync enqueued",
        "user_id": current_user.id,
        "date": date_str or date.today().isoformat(),
        "jobs": job_ids,
    }
