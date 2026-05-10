from fastapi import APIRouter

from app.api import automation, dashboard, devices, drift, health, health_checks, incidents, reports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(automation.router)
api_router.include_router(dashboard.router)
api_router.include_router(devices.router)
api_router.include_router(health_checks.router)
api_router.include_router(drift.router)
api_router.include_router(incidents.router)
api_router.include_router(reports.router)
