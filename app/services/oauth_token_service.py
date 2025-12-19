"""
Service for managing OAuth tokens
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.models.vendor_integration import OAuthToken
from app.services.encryption import token_encryption


class OAuthTokenService:
    """Service for OAuth token operations"""
    
    def store_tokens(
        self,
        db: Session,
        vendor_integration_id: int,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        token_type: str = "Bearer",
        scope: Optional[str] = None,
        user_id_from_vendor: Optional[str] = None
    ) -> OAuthToken:
        """
        Store encrypted OAuth tokens
        
        Args:
            db: Database session
            vendor_integration_id: Associated vendor integration ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiration time in seconds
            token_type: Token type (default: Bearer)
            scope: OAuth scope
            user_id_from_vendor: Vendor's user ID
            
        Returns:
            OAuthToken instance
        """
        # Calculate expiration datetime
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Encrypt tokens
        encrypted_access = token_encryption.encrypt(access_token)
        encrypted_refresh = token_encryption.encrypt(refresh_token) if refresh_token else None
        
        # Check if token already exists for this integration
        existing_token = db.query(OAuthToken).filter(
            OAuthToken.vendor_integration_id == vendor_integration_id
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.encrypted_access_token = encrypted_access
            existing_token.encrypted_refresh_token = encrypted_refresh
            existing_token.token_type = token_type
            existing_token.scope = scope
            existing_token.expires_at = expires_at
            existing_token.user_id_from_vendor = user_id_from_vendor
            existing_token.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_token)
            return existing_token
        
        # Create new token
        oauth_token = OAuthToken(
            vendor_integration_id=vendor_integration_id,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
            user_id_from_vendor=user_id_from_vendor
        )
        db.add(oauth_token)
        db.commit()
        db.refresh(oauth_token)
        return oauth_token
    
    def get_tokens(
        self,
        db: Session,
        vendor_integration_id: int
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Retrieve and decrypt OAuth tokens
        
        Args:
            db: Database session
            vendor_integration_id: Vendor integration ID
            
        Returns:
            Tuple of (access_token, refresh_token) or None if not found
        """
        oauth_token = db.query(OAuthToken).filter(
            OAuthToken.vendor_integration_id == vendor_integration_id
        ).first()
        
        if not oauth_token:
            return None
        
        # Decrypt tokens
        access_token = token_encryption.decrypt(oauth_token.encrypted_access_token)
        refresh_token = token_encryption.decrypt(oauth_token.encrypted_refresh_token) if oauth_token.encrypted_refresh_token else None
        
        return (access_token, refresh_token)
    
    def is_token_expired(
        self,
        db: Session,
        vendor_integration_id: int
    ) -> bool:
        """
        Check if the access token is expired
        
        Args:
            db: Database session
            vendor_integration_id: Vendor integration ID
            
        Returns:
            True if expired or not found, False otherwise
        """
        oauth_token = db.query(OAuthToken).filter(
            OAuthToken.vendor_integration_id == vendor_integration_id
        ).first()
        
        if not oauth_token or not oauth_token.expires_at:
            return True
        
        # Add a 5-minute buffer to refresh before actual expiration
        return datetime.utcnow() >= (oauth_token.expires_at - timedelta(minutes=5))
    
    def delete_tokens(
        self,
        db: Session,
        vendor_integration_id: int
    ) -> bool:
        """
        Delete OAuth tokens for a vendor integration
        
        Args:
            db: Database session
            vendor_integration_id: Vendor integration ID
            
        Returns:
            True if deleted, False if not found
        """
        oauth_token = db.query(OAuthToken).filter(
            OAuthToken.vendor_integration_id == vendor_integration_id
        ).first()
        
        if oauth_token:
            db.delete(oauth_token)
            db.commit()
            return True
        
        return False


oauth_token_service = OAuthTokenService()
