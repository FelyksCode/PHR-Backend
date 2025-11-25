from pydantic import BaseModel
from typing import Any, Dict, Optional

class FHIRResource(BaseModel):
    resourceType: str
    id: Optional[str] = None

class FHIRPatient(FHIRResource):
    resourceType: str = "Patient"
    name: Optional[list] = None
    telecom: Optional[list] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    address: Optional[list] = None

class FHIRObservation(FHIRResource):
    resourceType: str = "Observation"
    status: str
    category: Optional[list] = None
    code: Dict[str, Any]
    subject: Dict[str, Any]
    effectiveDateTime: Optional[str] = None
    valueQuantity: Optional[Dict[str, Any]] = None
    valueString: Optional[str] = None
    component: Optional[list] = None

class FHIRResponse(BaseModel):
    resourceType: str
    id: str
    meta: Optional[Dict[str, Any]] = None