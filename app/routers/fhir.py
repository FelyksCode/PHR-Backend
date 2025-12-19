from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.fhir.client import fhir_client
from app.auth.auth import get_current_active_user
from app.models.user import User
from app.schemas.fhir import FHIRCondition

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
    
    # Sort by date descending (latest first)
    params["_sort"] = "-date"
    
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

# Condition (Symptom) endpoints
@router.post("/Condition")
async def create_condition(
    condition_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Create a new Condition (symptom) resource in FHIR server"""
    # Ensure resource type is set
    condition_data["resourceType"] = "Condition"
    
    # If subject is not specified and user has fhir_patient_id, use it
    if "subject" not in condition_data and current_user.fhir_patient_id:
        condition_data["subject"] = {
            "reference": f"Patient/{current_user.fhir_patient_id}"
        }
    
    # Set default clinical status if not provided
    if "clinicalStatus" not in condition_data:
        condition_data["clinicalStatus"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active"
            }]
        }
    
    # Set default category if not provided
    if "category" not in condition_data:
        condition_data["category"] = [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item",
                "display": "Problem List Item"
            }]
        }]
    
    return await fhir_client.create_resource("Condition", condition_data)

@router.get("/Condition")
async def get_conditions(
    patient: Optional[str] = Query(None, description="Patient ID to filter conditions"),
    category: Optional[str] = Query(None, description="Condition category"),
    code: Optional[str] = Query(None, description="Condition code (SNOMED)"),
    clinical_status: Optional[str] = Query(None, alias="clinical-status", description="Clinical status (active, resolved, etc.)"),
    severity: Optional[str] = Query(None, description="Condition severity"),
    onset_date: Optional[str] = Query(None, alias="onset-date", description="Onset date range"),
    recorded_date: Optional[str] = Query(None, alias="recorded-date", description="Recorded date range"),
    _count: Optional[int] = Query(None, description="Number of results to return"),
    current_user: User = Depends(get_current_active_user)
):
    """Get Condition resources from FHIR server with optional filtering"""
    params = {}
    
    # If patient is not specified and user has fhir_patient_id, use it
    if not patient and current_user.fhir_patient_id:
        patient = current_user.fhir_patient_id
    
    # Check if user is accessing their own conditions
    if patient and current_user.fhir_patient_id and current_user.fhir_patient_id != patient:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access these conditions"
            )
    
    # Build query parameters
    if patient:
        params["patient"] = patient
    if category:
        params["category"] = category
    if code:
        params["code"] = code
    if clinical_status:
        params["clinical-status"] = clinical_status
    if severity:
        params["severity"] = severity
    if onset_date:
        params["onset-date"] = onset_date
    if recorded_date:
        params["recorded-date"] = recorded_date
    if _count:
        params["_count"] = str(_count)
    
    # Sort by recorded date descending (latest first)
    params["_sort"] = "-recorded-date"
    
    return await fhir_client.search_resources("Condition", **params)

@router.get("/Condition/{condition_id}")
async def get_condition(
    condition_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get Condition resource by ID from FHIR server"""
    condition = await fhir_client.get_resource("Condition", condition_id)
    
    # Check if user can access this condition (basic permission check)
    if current_user.fhir_patient_id:
        subject_ref = condition.get("subject", {}).get("reference", "")
        expected_ref = f"Patient/{current_user.fhir_patient_id}"
        
        if subject_ref != expected_ref and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this condition"
            )
    
    return condition

@router.put("/Condition/{condition_id}")
async def update_condition(
    condition_id: str,
    condition_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Update Condition resource in FHIR server"""
    # First get the existing condition to check permissions
    existing_condition = await fhir_client.get_resource("Condition", condition_id)
    
    # Check if user can access this condition
    if current_user.fhir_patient_id:
        subject_ref = existing_condition.get("subject", {}).get("reference", "")
        expected_ref = f"Patient/{current_user.fhir_patient_id}"
        
        if subject_ref != expected_ref and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to update this condition"
            )
    
    # Ensure resource type and ID are set
    condition_data["resourceType"] = "Condition"
    condition_data["id"] = condition_id
    
    return await fhir_client._make_request("PUT", f"Condition/{condition_id}", condition_data)

@router.delete("/Condition/{condition_id}")
async def delete_condition(
    condition_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete Condition resource from FHIR server"""
    # First get the existing condition to check permissions
    existing_condition = await fhir_client.get_resource("Condition", condition_id)
    
    # Check if user can access this condition
    if current_user.fhir_patient_id:
        subject_ref = existing_condition.get("subject", {}).get("reference", "")
        expected_ref = f"Patient/{current_user.fhir_patient_id}"
        
        if subject_ref != expected_ref and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to delete this condition"
            )
    
    return await fhir_client._make_request("DELETE", f"Condition/{condition_id}")

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