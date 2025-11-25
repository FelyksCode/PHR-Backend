from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import User
from app.models.user import Base
from app.routers import auth_router, users_router, fhir_router
from app.services.user_service import user_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create admin user if it doesn't exist
    db = next(get_db())
    try:
        admin_user = user_service.get_user_by_email(db, settings.admin_email)
        if not admin_user:
            user_service.create_admin_user(
                db=db,
                name="Admin User",
                email=settings.admin_email,
                password=settings.admin_password
            )
            print(f"Created admin user: {settings.admin_email}")
        else:
            print(f"Admin user already exists: {settings.admin_email}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown
    pass

# Create FastAPI app
app = FastAPI(
    title="PHR Backend API",
    description="Personal Health Record Backend with FHIR Integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(fhir_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PHR Backend API",
        "version": "1.0.0",
        "status": "running",
        "fhir_base_url": settings.fhir_base_url
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )