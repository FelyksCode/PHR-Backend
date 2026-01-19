"""
Service for managing vendor integrations
"""
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime

from app.models.vendor_integration import VendorIntegration, OAuthToken
from app.models.user import User


class VendorIntegrationService:
    """Service for vendor integration operations"""
    
    def create_integration(
        self,
        db: Session,
        user_id: int,
        vendor: str
    ) -> VendorIntegration:
        """
        Create or reactivate a vendor integration for a user
        
        Args:
            db: Database session
            user_id: User ID
            vendor: Vendor name (e.g., "fitbit")
            
        Returns:
            VendorIntegration instance
        """
        # Check if integration already exists
        existing = db.query(VendorIntegration).filter(
            and_(
                VendorIntegration.user_id == user_id,
                VendorIntegration.vendor == vendor
            )
        ).first()
        
        if existing:
            # Reactivate if it was disabled
            existing.is_active = True
            jakarta_tz = pytz.timezone('UTC')
            existing.updated_at = datetime.now(jakarta_tz)
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new integration
        integration = VendorIntegration(
            user_id=user_id,
            vendor=vendor,
            is_active=True
        )
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration
    
    def get_integration(
        self,
        db: Session,
        user_id: int,
        vendor: str
    ) -> Optional[VendorIntegration]:
        """
        Get a specific vendor integration for a user
        
        Args:
            db: Database session
            user_id: User ID
            vendor: Vendor name
            
        Returns:
            VendorIntegration instance or None
        """
        return db.query(VendorIntegration).filter(
            and_(
                VendorIntegration.user_id == user_id,
                VendorIntegration.vendor == vendor
            )
        ).first()
    
    def get_user_integrations(
        self,
        db: Session,
        user_id: int,
        active_only: bool = True
    ) -> List[VendorIntegration]:
        """
        Get all vendor integrations for a user
        
        Args:
            db: Database session
            user_id: User ID
            active_only: Only return active integrations
            
        Returns:
            List of VendorIntegration instances
        """
        query = db.query(VendorIntegration).filter(
            VendorIntegration.user_id == user_id
        )
        
        if active_only:
            query = query.filter(VendorIntegration.is_active == True)
        
        return query.all()
    
    def update_last_sync(
        self,
        db: Session,
        integration_id: int
    ) -> None:
        """
        Update the last sync timestamp for an integration
        
        Args:
            db: Database session
            integration_id: Integration ID
        """
        integration = db.query(VendorIntegration).filter(
            VendorIntegration.id == integration_id
        ).first()
        
        if integration:
            jakarta_tz = pytz.timezone('UTC')
            integration.last_sync_at = datetime.now(jakarta_tz)
            integration.updated_at = datetime.now(jakarta_tz)
            db.commit()
    
    def deactivate_integration(
        self,
        db: Session,
        integration_id: int
    ) -> bool:
        """
        Deactivate a vendor integration
        
        Args:
            db: Database session
            integration_id: Integration ID
            
        Returns:
            True if successful, False otherwise
        """
        integration = db.query(VendorIntegration).filter(
            VendorIntegration.id == integration_id
        ).first()
        jakarta_tz = pytz.timezone('UTC')

        if integration:
            integration.is_active = False
            integration.updated_at = datetime.now(jakarta_tz)
            db.commit()
            return True
        
        return False
    
    def disconnect_integration(
        self,
        db: Session,
        user_id: int,
        vendor: str
    ) -> bool:
        """
        Disconnect a vendor integration by deactivating it and removing OAuth tokens
        
        Args:
            db: Database session
            user_id: User ID
            vendor: Vendor name
            
        Returns:
            True if successful, False otherwise
        """
        from app.services.oauth_token_service import oauth_token_service
        
        # Get the integration
        integration = self.get_integration(db, user_id, vendor)
        
        if not integration:
            return False
        
        # Delete OAuth tokens
        oauth_token_service.delete_tokens(db, integration.id)
        
        # Deactivate the integration
        jakarta_tz = pytz.timezone('UTC')
        integration.is_active = False
        integration.updated_at = datetime.now(jakarta_tz)
        db.commit()
        
        return True


vendor_integration_service = VendorIntegrationService()
