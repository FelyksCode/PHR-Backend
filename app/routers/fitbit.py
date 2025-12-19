"""
Fitbit OAuth integration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
import secrets
import base64
from typing import Optional
from urllib.parse import urlencode

from app.database import get_db
from app.auth.auth import get_current_user
from app.models.user import User
from app.config import settings
from app.schemas.vendor import OAuthTokenResponse
from app.services.vendor_integration_service import vendor_integration_service
from app.services.oauth_token_service import oauth_token_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/integrations/fitbit",
    tags=["fitbit"]
)

# Store state tokens temporarily (in production, use Redis or database)
# This is a simple in-memory store for demo purposes
oauth_states = {}


@router.get("/authorize")
async def fitbit_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Fitbit OAuth 2.0 authorization flow
    
    Redirects user to Fitbit's authorization page where they can
    grant permission using their Google account.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Redirect to Fitbit OAuth page
    """
    # Verify Fitbit credentials are configured
    if not settings.fitbit_client_id or not settings.fitbit_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fitbit OAuth credentials not configured"
        )
    
    # Check if user has selected Fitbit vendor
    integration = vendor_integration_service.get_integration(
        db=db,
        user_id=current_user.id,
        vendor="fitbit"
    )
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select Fitbit vendor first using POST /integrations/vendors/select"
        )
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "user_id": current_user.id,
        "integration_id": integration.id
    }
    
    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": settings.fitbit_client_id,
        "redirect_uri": settings.fitbit_redirect_uri,
        "scope": "activity heartrate oxygen_saturation weight profile",
        "state": state
    }
    
    auth_url = f"{settings.fitbit_oauth_url}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def fitbit_callback(
    code: str = Query(..., description="Authorization code from Fitbit"),
    state: str = Query(..., description="State token for CSRF protection"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Fitbit
    
    Exchanges authorization code for access and refresh tokens,
    stores them encrypted in the database.
    
    Args:
        code: Authorization code from Fitbit
        state: State token for verification
        db: Database session
        
    Returns:
        Success message with token information
    """
    # Verify state token
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )
    
    oauth_data = oauth_states.pop(state)
    user_id = oauth_data["user_id"]
    integration_id = oauth_data["integration_id"]
    
    # Exchange code for tokens
    try:
        # Prepare Basic Auth header
        credentials = f"{settings.fitbit_client_id}:{settings.fitbit_client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.fitbit_redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.fitbit_token_url,
                headers=headers,
                data=data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Fitbit token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for tokens: {response.text}"
                )
            
            token_data = response.json()
        
        # Store tokens
        oauth_token_service.store_tokens(
            db=db,
            vendor_integration_id=integration_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data["expires_in"],
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope"),
            user_id_from_vendor=token_data.get("user_id")
        )
        
        logger.info(f"Successfully stored Fitbit OAuth tokens for user {user_id}")
        
        return {
            "message": "Successfully connected to Fitbit",
            "vendor": "fitbit",
            "user_id": user_id,
            "fitbit_user_id": token_data.get("user_id")
        }
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during Fitbit OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Fitbit: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error during Fitbit OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get("/status")
async def fitbit_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check Fitbit connection status for the current user
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Connection status information
    """
    integration = vendor_integration_service.get_integration(
        db=db,
        user_id=current_user.id,
        vendor="fitbit"
    )
    
    if not integration or not integration.is_active:
        return {
            "connected": False,
            "message": "Fitbit not connected"
        }
    
    tokens = oauth_token_service.get_tokens(db, integration.id)
    if not tokens:
        return {
            "connected": False,
            "message": "No OAuth tokens found"
        }
    
    is_expired = oauth_token_service.is_token_expired(db, integration.id)
    
    return {
        "connected": True,
        "vendor": "fitbit",
        "integration_id": integration.id,
        "last_sync": integration.last_sync_at,
        "token_expired": is_expired
    }
