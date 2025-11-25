from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.auth.auth import get_password_hash, verify_password
from app.fhir.client import fhir_client

class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    async def create_user(db: Session, user_create: UserCreate) -> User:
        """Create a new user and associated FHIR Patient"""
        # Check if user already exists
        existing_user = UserService.get_user_by_email(db, user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create FHIR Patient first
        patient_data = {
            "resourceType": "Patient",
            "name": [
                {
                    "use": "official",
                    "family": user_create.name.split()[-1] if " " in user_create.name else user_create.name,
                    "given": [user_create.name.split()[0]] if " " in user_create.name else []
                }
            ],
            "telecom": [
                {
                    "system": "email",
                    "value": user_create.email,
                    "use": "home"
                }
            ],
            "active": True
        }
        
        try:
            fhir_response = await fhir_client.create_patient(patient_data)
            fhir_patient_id = fhir_response.get("id")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create FHIR patient: {str(e)}"
            )
        
        # Create local user record
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            name=user_create.name,
            email=user_create.email,
            password_hash=hashed_password,
            fhir_patient_id=fhir_patient_id
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user"""
        db_user = UserService.get_user_by_id(db, user_id)
        if not db_user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Handle password update
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete user"""
        db_user = UserService.get_user_by_id(db, user_id)
        if not db_user:
            return False
        
        db.delete(db_user)
        db.commit()
        
        return True
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user
    
    @staticmethod
    def create_admin_user(db: Session, name: str, email: str, password: str) -> User:
        """Create admin user"""
        hashed_password = get_password_hash(password)
        db_user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            is_admin=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user

user_service = UserService()