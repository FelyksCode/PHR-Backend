"""
Database models for vendor integrations and OAuth tokens
"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class VendorIntegration(Base):
    """
    Stores user-vendor associations
    Tracks which vendors each user has connected
    """
    __tablename__ = "vendor_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vendor = Column(String, nullable=False)  # e.g., "fitbit", "apple_health", etc.
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="vendor_integrations")
    oauth_tokens = relationship("OAuthToken", back_populates="vendor_integration", cascade="all, delete-orphan")


class OAuthToken(Base):
    """
    Stores encrypted OAuth tokens for vendor integrations
    Supports token refresh and expiration tracking
    """
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    vendor_integration_id = Column(Integer, ForeignKey("vendor_integrations.id"), nullable=False, index=True)
    
    # Encrypted token data (using Fernet encryption)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    
    # Token metadata
    token_type = Column(String, default="Bearer")
    scope = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Fitbit-specific fields
    user_id_from_vendor = Column(String, nullable=True)  # Fitbit user ID
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor_integration = relationship("VendorIntegration", back_populates="oauth_tokens")
