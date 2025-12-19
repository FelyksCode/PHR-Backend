"""
Fitbit API client service
Handles data fetching, token refresh, and API interactions
"""
import httpx
import base64
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
import logging

from app.config import settings
from app.services.oauth_token_service import oauth_token_service
from app.services.vendor_integration_service import vendor_integration_service

logger = logging.getLogger(__name__)


class FitbitAPIError(Exception):
    """Custom exception for Fitbit API errors"""
    pass


class FitbitService:
    """
    Service for interacting with Fitbit Web API
    Handles authentication, token refresh, and data fetching
    """
    
    def __init__(self):
        self.api_url = settings.fitbit_api_url
        self.token_url = settings.fitbit_token_url
    
    async def _refresh_access_token(
        self,
        db: Session,
        vendor_integration_id: int,
        refresh_token: str
    ) -> str:
        """
        Refresh the access token using refresh token
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            refresh_token: Current refresh token
            
        Returns:
            New access token
            
        Raises:
            FitbitAPIError: If token refresh fails
        """
        try:
            # Prepare Basic Auth header
            credentials = f"{settings.fitbit_client_id}:{settings.fitbit_client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    headers=headers,
                    data=data,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    raise FitbitAPIError(f"Failed to refresh token: {response.text}")
                
                token_data = response.json()
            
            # Store new tokens
            oauth_token_service.store_tokens(
                db=db,
                vendor_integration_id=vendor_integration_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data["expires_in"],
                token_type=token_data.get("token_type", "Bearer"),
                scope=token_data.get("scope"),
                user_id_from_vendor=token_data.get("user_id")
            )
            
            logger.info(f"Successfully refreshed Fitbit token for integration {vendor_integration_id}")
            return token_data["access_token"]
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token refresh: {str(e)}")
            raise FitbitAPIError(f"HTTP error during token refresh: {str(e)}")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise FitbitAPIError(f"Error refreshing token: {str(e)}")
    
    async def _get_valid_access_token(
        self,
        db: Session,
        vendor_integration_id: int
    ) -> str:
        """
        Get a valid access token, refreshing if necessary
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            
        Returns:
            Valid access token
            
        Raises:
            FitbitAPIError: If unable to get valid token
        """
        tokens = oauth_token_service.get_tokens(db, vendor_integration_id)
        if not tokens:
            raise FitbitAPIError("No OAuth tokens found for this integration")
        
        access_token, refresh_token = tokens
        
        # Check if token is expired
        if oauth_token_service.is_token_expired(db, vendor_integration_id):
            if not refresh_token:
                raise FitbitAPIError("Token expired and no refresh token available")
            
            # Refresh the token
            access_token = await self._refresh_access_token(
                db, vendor_integration_id, refresh_token
            )
        
        return access_token
    
    async def _make_api_request(
        self,
        db: Session,
        vendor_integration_id: int,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None
    ) -> Dict[Any, Any]:
        """
        Make an authenticated request to Fitbit API
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            endpoint: API endpoint (e.g., "/1/user/-/profile.json")
            method: HTTP method
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            FitbitAPIError: If API request fails
        """
        access_token = await self._get_valid_access_token(db, vendor_integration_id)
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        url = f"{self.api_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=30.0
                    )
                else:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        timeout=30.0
                    )
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning(f"Fitbit API rate limit reached for integration {vendor_integration_id}")
                    raise FitbitAPIError("Rate limit exceeded. Please try again later.")
                
                if response.status_code != 200:
                    logger.error(f"Fitbit API error: {response.status_code} - {response.text}")
                    raise FitbitAPIError(f"API request failed: {response.text}")
                
                return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during API request: {str(e)}")
            raise FitbitAPIError(f"HTTP error: {str(e)}")
    
    async def get_heart_rate(
        self,
        db: Session,
        vendor_integration_id: int,
        date_str: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Fetch heart rate data for a specific date
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Heart rate data
        """
        if not date_str:
            date_str = date.today().isoformat()
        
        endpoint = f"/1/user/-/activities/heart/date/{date_str}/1d.json"
        return await self._make_api_request(db, vendor_integration_id, endpoint)
    
    async def get_spo2(
        self,
        db: Session,
        vendor_integration_id: int,
        date_str: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Fetch SpO2 (blood oxygen saturation) data for a specific date
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            SpO2 data
        """
        if not date_str:
            date_str = date.today().isoformat()
        
        endpoint = f"/1/user/-/spo2/date/{date_str}.json"
        return await self._make_api_request(db, vendor_integration_id, endpoint)
    
    async def get_body_weight(
        self,
        db: Session,
        vendor_integration_id: int,
        date_str: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Fetch body weight data for a specific date
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Weight data
        """
        if not date_str:
            date_str = date.today().isoformat()
        
        endpoint = f"/1/user/-/body/log/weight/date/{date_str}.json"
        return await self._make_api_request(db, vendor_integration_id, endpoint)
    
    async def get_activity_summary(
        self,
        db: Session,
        vendor_integration_id: int,
        date_str: Optional[str] = None
    ) -> Dict[Any, Any]:
        """
        Fetch activity summary for a specific date
        
        Args:
            db: Database session
            vendor_integration_id: Integration ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Activity summary data
        """
        if not date_str:
            date_str = date.today().isoformat()
        
        endpoint = f"/1/user/-/activities/date/{date_str}.json"
        return await self._make_api_request(db, vendor_integration_id, endpoint)
    
    async def fetch_all_health_data(
        self,
        db: Session,
        user_id: int,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all available health data for a user
        
        Args:
            db: Database session
            user_id: User ID
            date_str: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Dictionary containing all health data
            
        Raises:
            FitbitAPIError: If user has no Fitbit integration
        """
        # Get user's Fitbit integration
        integration = vendor_integration_service.get_integration(
            db=db,
            user_id=user_id,
            vendor="fitbit"
        )
        
        if not integration or not integration.is_active:
            raise FitbitAPIError("User has no active Fitbit integration")
        
        # Fetch all data types
        results = {
            "date": date_str or date.today().isoformat(),
            "heart_rate": None,
            "spo2": None,
            "body_weight": None,
            "activity_summary": None
        }
        
        try:
            results["heart_rate"] = await self.get_heart_rate(
                db, integration.id, date_str
            )
        except FitbitAPIError as e:
            logger.warning(f"Failed to fetch heart rate: {str(e)}")
        
        try:
            results["spo2"] = await self.get_spo2(
                db, integration.id, date_str
            )
        except FitbitAPIError as e:
            logger.warning(f"Failed to fetch SpO2: {str(e)}")
        
        try:
            results["body_weight"] = await self.get_body_weight(
                db, integration.id, date_str
            )
        except FitbitAPIError as e:
            logger.warning(f"Failed to fetch body weight: {str(e)}")
        
        try:
            results["activity_summary"] = await self.get_activity_summary(
                db, integration.id, date_str
            )
        except FitbitAPIError as e:
            logger.warning(f"Failed to fetch activity summary: {str(e)}")
        
        return results


fitbit_service = FitbitService()
