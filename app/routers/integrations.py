"""
API endpoints for vendor integrations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth.auth import get_current_user
from app.models.user import User
from app.models.vendor_integration import VendorIntegration
from app.schemas.vendor import (
    VendorSelectionRequest,
    VendorSelectionResponse,
    VendorDisconnectRequest,
    VendorDisconnectResponse,
    VendorIntegrationListResponse,
    VendorIntegrationInfo,
    VendorType
)
from app.services.vendor_integration_service import vendor_integration_service

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"]
)


@router.post("/vendors/select", response_model=VendorSelectionResponse)
async def select_vendor(
    request: VendorSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Select and activate a vendor integration for the authenticated user
    
    Creates a vendor integration record that can later be used for OAuth flow.
    If the integration already exists, it will be reactivated.
    
    Args:
        request: Vendor selection request containing vendor type
        current_user: Authenticated user
        db: Database session
        
    Returns:
        VendorSelectionResponse with integration details
    """
    try:
        # Create or reactivate the integration
        integration = vendor_integration_service.create_integration(
            db=db,
            user_id=current_user.id,
            vendor=request.vendor.value
        )
        
        return VendorSelectionResponse(
            message=f"Successfully selected {request.vendor.value} integration",
            vendor=request.vendor.value,
            integration_id=integration.id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor integration: {str(e)}"
        )


@router.post("/vendors/disconnect", response_model=VendorDisconnectResponse)
async def disconnect_vendor(
    request: VendorDisconnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a vendor integration for the authenticated user
    
    Deactivates the vendor integration and removes all associated OAuth tokens.
    This will stop data syncing and revoke access to the vendor's API.
    
    Args:
        request: Vendor disconnect request containing vendor type
        current_user: Authenticated user
        db: Database session
        
    Returns:
        VendorDisconnectResponse with disconnection confirmation
    """
    # Check if integration exists
    integration = vendor_integration_service.get_integration(
        db=db,
        user_id=current_user.id,
        vendor=request.vendor.value
    )
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {request.vendor.value} integration found for this user"
        )
    
    if not integration.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{request.vendor.value} integration is already disconnected"
        )
    
    # Disconnect the integration
    success = vendor_integration_service.disconnect_integration(
        db=db,
        user_id=current_user.id,
        vendor=request.vendor.value
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect {request.vendor.value} integration"
        )
    
    return VendorDisconnectResponse(
        message=f"Successfully disconnected {request.vendor.value} integration",
        vendor=request.vendor.value
    )


@router.get("/vendors", response_model=VendorIntegrationListResponse)
async def list_vendor_integrations(
    active_only: bool = Query(True, description="Only return active integrations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all vendor integrations for the authenticated user
    
    Args:
        active_only: Filter to only active integrations
        current_user: Authenticated user
        db: Database session
        
    Returns:
        VendorIntegrationListResponse with list of integrations
    """
    integrations = vendor_integration_service.get_user_integrations(
        db=db,
        user_id=current_user.id,
        active_only=active_only
    )

    # Convert last_sync_at from UTC to the user's timezone before returning
    user_tz_name = current_user.timezone or "UTC"
    try:
        import pytz
        user_tz = pytz.timezone(user_tz_name)
    except Exception:
        # Fallback safely to UTC if timezone is invalid
        import pytz
        user_tz = pytz.timezone("UTC")

    integration_infos = []
    for integration in integrations:
        last_sync_at_local = None
        if integration.last_sync_at is not None:
            # Ensure the datetime is timezone-aware in UTC, then convert
            try:
                if integration.last_sync_at.tzinfo is None:
                    import pytz
                    last_sync_at_utc = pytz.UTC.localize(integration.last_sync_at)
                else:
                    last_sync_at_utc = integration.last_sync_at
                last_sync_at_local = last_sync_at_utc.astimezone(user_tz)
            except Exception:
                # If conversion fails, leave as original value
                last_sync_at_local = integration.last_sync_at

        integration_infos.append(
            VendorIntegrationInfo(
                id=integration.id,
                vendor=integration.vendor,
                is_active=integration.is_active,
                last_sync_at=last_sync_at_local,
                created_at=integration.created_at,
            )
        )

    return VendorIntegrationListResponse(integrations=integration_infos)


@router.delete("/vendors/{integration_id}")
async def deactivate_vendor_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a vendor integration
    
    Args:
        integration_id: Integration ID to deactivate
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    # Verify the integration belongs to the current user
    integration = db.query(VendorIntegration).filter(
        VendorIntegration.id == integration_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor integration not found"
        )
    
    if integration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this integration"
        )
    
    success = vendor_integration_service.deactivate_integration(
        db=db,
        integration_id=integration_id
    )
    
    if success:
        return {"message": "Vendor integration deactivated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate vendor integration"
        )
