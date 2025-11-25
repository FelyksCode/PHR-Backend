from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./phr.db")
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # FHIR
    fhir_base_url: str = os.getenv("FHIR_BASE_URL", "http://localhost:8080/fhir")
    
    # Admin
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@phr.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"

settings = Settings()