from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.fhir.client import fhir_client
from app.auth.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/fhir", tags=["FHIR"])

@router.post("/Patient")
async def create_patient(
    patient_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Create a new Patient resource in FHIR server"""
    # Ensure resource type is set
    patient_data["resourceType"] = "Patient"
    
    return await fhir_client.create_patient(patient_data)

@router.get("/Patient/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Patient resource by ID from FHIR server"""
    # Check if user is accessing their own patient record (if fhir_patient_id is set)
    if current_user.fhir_patient_id and current_user.fhir_patient_id != patient_id:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this patient record"
            )
    
    return await fhir_client.get_patient(patient_id)

@router.put("/Patient/{patient_id}")
async def update_patient(
    patient_id: str,
    patient_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Update Patient resource in FHIR server"""
    # Check permissions
    if current_user.fhir_patient_id and current_user.fhir_patient_id != patient_id:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to update this patient record"
            )
    
    # Ensure resource type and ID are set
    patient_data["resourceType"] = "Patient"
    patient_data["id"] = patient_id
    
    return await fhir_client.update_patient(patient_id, patient_data)

@router.post("/Observation")
async def create_observation(
    observation_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Create a new Observation resource in FHIR server"""
    # Ensure resource type is set
    observation_data["resourceType"] = "Observation"
    
    # If subject is not specified and user has fhir_patient_id, use it
    if "subject" not in observation_data and current_user.fhir_patient_id:
        observation_data["subject"] = {
            "reference": f"Patient/{current_user.fhir_patient_id}"
        }
    
    return await fhir_client.create_observation(observation_data)

@router.get("/Observation")
async def get_observations(
    patient: Optional[str] = Query(None, description="Patient ID to filter observations"),
    category: Optional[str] = Query(None, description="Observation category"),
    code: Optional[str] = Query(None, description="Observation code"),
    date: Optional[str] = Query(None, description="Date range (e.g., ge2023-01-01)"),
    _count: Optional[int] = Query(None, description="Number of results to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Get Observation resources from FHIR server with optional filtering"""
    params = {}
    
    # If patient is not specified and user has fhir_patient_id, use it
    if not patient and current_user.fhir_patient_id:
        patient = current_user.fhir_patient_id
    
    # Check if user is accessing their own observations
    if patient and current_user.fhir_patient_id and current_user.fhir_patient_id != patient:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access these observations"
            )
    
    # Build query parameters
    if patient:
        params["patient"] = patient
    if category:
        params["category"] = category
    if code:
        params["code"] = code
    if date:
        params["date"] = date
    if _count:
        params["_count"] = str(_count)
    
    return await fhir_client.get_observations(**params)

@router.get("/Observation/{observation_id}")
async def get_observation(
    observation_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Observation resource by ID from FHIR server"""
    observation = await fhir_client.get_observation(observation_id)
    
    # Check if user can access this observation (basic permission check)
    if current_user.fhir_patient_id:
        subject_ref = observation.get("subject", {}).get("reference", "")
        expected_ref = f"Patient/{current_user.fhir_patient_id}"
        
        if subject_ref != expected_ref and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this observation"
            )
    
    return observation

@router.get("/{resource_type}")
async def search_fhir_resources(
    resource_type: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Generic search for any FHIR resource type"""
    # Get all query parameters
    params = dict(request.query_params)
    
    # Add patient filter for user's own data if applicable
    if resource_type in ["Observation", "Condition", "MedicationRequest", "Procedure"]:
        if "patient" not in params and current_user.fhir_patient_id:
            params["patient"] = current_user.fhir_patient_id
    
    return await fhir_client.search_resources(resource_type, **params)

@router.post("/{resource_type}")
async def create_fhir_resource(
    resource_type: str,
    resource_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Create any FHIR resource"""
    # Ensure resource type is set
    resource_data["resourceType"] = resource_type
    
    return await fhir_client.create_resource(resource_type, resource_data)

@router.get("/{resource_type}/{resource_id}")
async def get_fhir_resource(
    resource_type: str,
    resource_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get any FHIR resource by type and ID"""
    return await fhir_client.get_resource(resource_type, resource_id)