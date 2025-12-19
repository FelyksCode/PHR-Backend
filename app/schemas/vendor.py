"""
Pydantic schemas for vendor integrations
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class VendorType(str, Enum):
    """Supported vendor types"""
    FITBIT = "fitbit"


class VendorSelectionRequest(BaseModel):
    """Request body for selecting a vendor"""
    vendor: VendorType = Field(..., description="Health data vendor to connect")


class VendorSelectionResponse(BaseModel):
    """Response after selecting a vendor"""
    message: str
    vendor: str
    integration_id: int
    
    class Config:
        from_attributes = True


class OAuthTokenResponse(BaseModel):
    """Response after successful OAuth"""
    message: str
    vendor: str
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class VendorIntegrationInfo(BaseModel):
    """Information about a vendor integration"""
    id: int
    vendor: str
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class VendorIntegrationListResponse(BaseModel):
    """List of user's vendor integrations"""
    integrations: List[VendorIntegrationInfo]
    
    class Config:
        from_attributes = True


class FitbitHealthData(BaseModel):
    """Raw Fitbit health data structure"""
    heart_rate: Optional[List[dict]] = None
    spo2: Optional[List[dict]] = None
    body_weight: Optional[List[dict]] = None
    activities: Optional[List[dict]] = None


class HealthObservation(BaseModel):
    """Vendor-agnostic health observation"""
    id: str
    code: str
    code_system: str
    display: str
    value: float
    unit: str
    effective_datetime: datetime
    patient_id: str
    
    class Config:
        from_attributes = True


class HealthObservationsResponse(BaseModel):
    """Paginated health observations response"""
    observations: List[HealthObservation]
    total: int
    page: int
    page_size: int
    has_more: bool
    
    class Config:
        from_attributes = True
