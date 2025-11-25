from .auth import router as auth_router
from .users import router as users_router
from .fhir import router as fhir_router

__all__ = ["auth_router", "users_router", "fhir_router"]