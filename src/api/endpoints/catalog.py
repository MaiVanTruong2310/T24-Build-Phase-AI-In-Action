"""Compatibility facade for the split catalog endpoint modules."""

from src.api.endpoints import doctor, facility, schedule, service, specialty
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.endpoints.doctor import _doctor_response
from src.api.endpoints.schedule import _availability_window

__all__ = ["_availability_window", "_doctor_response", "get_catalog_service", "router", "staff_router"]

# Import domain modules above so their route declarations register on the
# shared routers while existing imports keep working.
del doctor, facility, schedule, service, specialty
