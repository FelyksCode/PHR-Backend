from .auth import router as auth_router
from .users import router as users_router
from .fhir import router as fhir_router
from .integrations import router as integrations_router
from .fitbit import router as fitbit_router
from .health import router as health_router

__all__ = ["auth_router", "users_router", "fhir_router", "integrations_router", "fitbit_router", "health_router"]