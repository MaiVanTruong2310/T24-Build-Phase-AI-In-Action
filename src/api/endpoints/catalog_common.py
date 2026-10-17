"""Shared routers and dependency wiring for catalog domain endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dependencies import get_db_session
from src.services.catalog import CatalogService

router = APIRouter(tags=["catalog"])
staff_router = APIRouter(prefix="/staff", tags=["staff-catalog"])


def get_catalog_service(session: AsyncSession = Depends(get_db_session)) -> CatalogService:
    """Build the service for the current request."""
    return CatalogService(session)
