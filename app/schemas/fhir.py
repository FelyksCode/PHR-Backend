from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, Optional

class FHIRResource(BaseModel):
    resourceType: str
    id: Optional[str] = None


class ObservationStatus(str, Enum):
    REGISTERED = "registered"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"
    APPENDED = "appended"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered-in-error"
    UNKNOWN = "unknown"

class FHIRPatient(FHIRResource):
    resourceType: str = "Patient"
    name: Optional[list] = None
    telecom: Optional[list] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    address: Optional[list] = None

class FHIRObservation(FHIRResource):
    resourceType: str = "Observation"
    status: ObservationStatus
    category: Optional[list] = None
    code: Dict[str, Any]
    subject: Dict[str, Any]
    effectiveDateTime: Optional[str] = None
    valueQuantity: Optional[Dict[str, Any]] = None
    valueString: Optional[str] = None
    component: Optional[list] = None

class FHIRCondition(FHIRResource):
    resourceType: str = "Condition"
    code: Dict[str, Any]  # CodeableConcept with SNOMED code
    clinicalStatus: Dict[str, Any]  # active | recurrence | relapse | inactive | remission | resolved | unknown
    category: Optional[list] = None  # CodeableConcept category
    severity: Optional[Dict[str, Any]] = None  # CodeableConcept (mild/moderate/high)
    subject: Dict[str, Any]  # Reference to Patient
    onsetDateTime: Optional[str] = None  # When condition started
    recordedDate: Optional[str] = None  # When condition was first recorded
    recorder: Optional[Dict[str, Any]] = None  # Who recorded the condition
    note: Optional[list] = None  # Additional notes

class FHIRResponse(BaseModel):
    resourceType: str
    id: str
    meta: Optional[Dict[str, Any]] = None