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
    
    # Fitbit OAuth
    fitbit_client_id: str = os.getenv("FITBIT_CLIENT_ID", "")
    fitbit_client_secret: str = os.getenv("FITBIT_CLIENT_SECRET", "")
    fitbit_redirect_uri: str = os.getenv("FITBIT_REDIRECT_URI", "http://localhost:8000/integrations/fitbit/callback")
    fitbit_oauth_url: str = "https://www.fitbit.com/oauth2/authorize"
    fitbit_token_url: str = "https://api.fitbit.com/oauth2/token"
    fitbit_api_url: str = "https://api.fitbit.com"
    
    # Encryption key for storing OAuth tokens (should be 32 bytes for Fernet)
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    
    # Admin
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@phr.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"

settings = Settings()